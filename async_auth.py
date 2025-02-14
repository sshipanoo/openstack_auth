import requests
from pprint import pprint
import asyncio
from concurrent.futures import ThreadPoolExecutor

# OpenStack Keystone 认证 URL
base_url = "http://keystone.openstack.xxxxx.com/v3"

user_name = ""
password = ""
domain_name = "Default"

auth_url = f"{base_url}/auth/tokens"
projects_url = f"{base_url}/projects"

# 全局变量
auth_token = None
response_data = None

# 获取认证 Token
def get_auth_token():
    try:
        auth_data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": user_name,
                            "password": password,
                            "domain": {"name": domain_name}
                        }
                    }
                }
            }
        }
        response = requests.post(auth_url, json=auth_data, headers={"Content-Type": "application/json"})
        token = response.headers["X-Subject-Token"]
        return token, response.json()
    except Exception as e:
        print(f"获取认证 Token 失败: {e}")
        return None, None

# 获取指定项目的 Token
def get_project_token(project_id):
    try:
        auth_data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": user_name,
                            "password": password,
                            "domain": {"name": domain_name}
                        }
                    }
                },
                "scope": {
                    "project": {
                        "id": project_id
                    }
                }
            }
        }
        response = requests.post(auth_url, json=auth_data, headers={"Content-Type": "application/json"})
        token_key = 'X-Subject-Token'
        if token_key not in response.headers:
            token_key = token_key.lower()
        if token_key not in response.headers:
            return None, None
        token = response.headers[token_key]
        return token, response.json()
    except Exception as e:
        print(f"获取项目 Token 失败: {e}")
        return None, None

# 获取 Nova URL
def get_nova_url(data):
    catalog = data.get('token', {}).get('catalog', [])
    for cat in catalog:
        if cat.get('name') == 'nova' and cat.get('type') == 'compute':
            for endpoint in cat.get('endpoints', []):
                if endpoint.get('interface') == 'public':
                    url = endpoint.get('url')
                    return "/".join(url.split("/")[:-1])
    return None

# 获取所有项目
def get_projects():
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }
    response = requests.get(projects_url, headers=headers)
    return response.json().get('projects', [])

# 获取指定项目的虚拟机
def get_project_servers(project_id, data, headers):
    nova_url = get_nova_url(data)
    if not nova_url:
        return []
    server_url = f"{nova_url}/{project_id}/servers"
    response = requests.get(server_url, headers=headers)
    return response.json().get('servers', [])

# 异步获取指定项目的虚拟机
async def async_get_project_servers(project):
    project_id = project['id']
    print(f"开始获取项目 {project['name']} 的虚拟机...")
    project_token, data = get_project_token(project_id)
    if not project_token:
        print(f"获取项目 {project['name']} 的 Token 失败")
        return project, []
    headers = {
        "X-Auth-Token": project_token,
        "Content-Type": "application/json"
    }
    servers = get_project_servers(project_id, data, headers)
    print(f"完成获取项目 {project['name']} 的虚拟机: {len(servers)} 台")
    return project, servers

# 主函数
async def main():
    global auth_token, response_data
    auth_token, response_data = get_auth_token()
    if not auth_token:
        print("认证失败，请检查用户名、密码或认证 URL")
        return

    # 获取所有项目
    all_projects = get_projects()
    print(f"总共项目数量: {len(all_projects)}")

    # 使用 asyncio.gather 并发获取虚拟机
    tasks = [async_get_project_servers(project) for project in all_projects]
    results = await asyncio.gather(*tasks)

    # 处理结果
    ok_project_count = 0
    all_server_count = 0
    ok_project_names = []
    project_vms = []

    for project, servers in results:
        if servers:
            ok_project_count += 1
            ok_project_names.append(project['name'])
            all_server_count += len(servers)
            for server in servers:
                project_vms.append({
                    "project_name": project['name'],
                    "vm_id": server['id'],
                    "vm_name": server['name']
                })

    # 打印统计信息
    print("=====================================")
    print(f"获取到 server 的项目数量: {ok_project_count}")
    print(f"获取到 server 的项目名称: {ok_project_names}")
    print(f"获取到 server 的总数量: {all_server_count}")

    # 打印树状结构的虚拟机信息
    print("\n所有项目的虚拟机信息:")
    current_project = None
    for index, vm in enumerate(project_vms):
        if vm['project_name'] != current_project:
            current_project = vm['project_name']
            print(f"项目{current_project}")
        is_last_vm = index == len(project_vms) - 1 or project_vms[index + 1]['project_name'] != current_project
        prefix = "└──" if is_last_vm else "├──"
        print(f"{prefix} 虚拟机 ID:{vm['vm_id']}  名称:{vm['vm_name']}")

# 运行主函数
if __name__ == "__main__":
    asyncio.run(main())