import aiohttp
import asyncio
from pprint import pprint

# OpenStack Keystone 认证 URL
base_url = "http://xxxx/v3"

user_name = ""
password = ""
domain_name = "Default"
project_name = 'admin'




auth_url = f"{base_url}/auth/tokens"
region_url = f"{base_url}/regions"
donmain_url = f"{base_url}/domains"
# images_url = f"{base_url}/images"


# 全局变量
auth_token = None
response_data = None

# 获取认证 Token
async def get_auth_token():
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
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json=auth_data, headers={"Content-Type": "application/json"}) as response:
                token = response.headers.get("X-Subject-Token")
                data = await response.json()
                user_id = data.get('token').get('user').get('id')
                return token, data,user_id
    except Exception as e:
        print(f"获取认证 Token 失败: {e}")
        return None, None

# 获取指定项目的 Token
async def get_project_token(project_id):
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
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json=auth_data, headers={"Content-Type": "application/json"}) as response:
                token_key = 'X-Subject-Token'
                token = response.headers.get(token_key) or response.headers.get(token_key.lower())
                data = await response.json()
                return token, data
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

# 获取所有镜像
def get_images_url(data):
    catalog = data.get('token', {}).get('catalog', [])
    for cat in catalog:
        if cat.get('name') == 'glance' and cat.get('type') == 'image':
            for endpoint in cat.get('endpoints', []):
                if endpoint.get('interface') == 'public':
                    url = endpoint.get('url')
                    return "/".join(url.split("/")[:-1])
    return None


# 获取所有项目
async def get_projects():
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:

        projects_url = f"{base_url}/users/{user_id}/projects"
        async with session.get(projects_url, headers=headers) as response:
            data = await response.json()
            return data.get('projects', [])
        
async def get_images(data, project_id=None):
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }

    image_url = get_images_url(data=data)

    if project_id:
        images_url = f'{image_url}/{project_id}/v2/images'
    else:
        images_url = f'{image_url}/v2/images'

    print(f"images_url: {images_url}")

    async with aiohttp.ClientSession() as session:
        async with session.get(image_url, headers=headers) as response:
            data = await response.json()
            return data.get('images', [])

        
async def get_regions():
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(region_url, headers=headers) as response:
            data = await response.json()
            return data.get('regions', [])
        
async def get_domains():
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(donmain_url, headers=headers) as response:
            data = await response.json()
            try:
                return data.get('domains', [])
            except Exception as e:
                print(f"获取项目 Token 失败: {e}")
                return []
            


# 获取指定项目的虚拟机
async def get_project_servers(project_id, data, headers):
    nova_url = get_nova_url(data)
    if not nova_url:
        return []
    server_url = f"{nova_url}/{project_id}/servers"
    async with aiohttp.ClientSession() as session:
        async with session.get(server_url, headers=headers) as response:
            data = await response.json()
            return data.get('servers', [])

# 异步获取指定项目的虚拟机
async def async_get_project_servers(project, semaphore):
    async with semaphore:
        project_id = project['id']
        print(f"开始获取项目 {project['name']} 的虚拟机...")
        project_token, data = await get_project_token(project_id)
        if not project_token:
            print(f"获取项目 {project['name']} 的 Token 失败")
            return project, []
        headers = {
            "X-Auth-Token": project_token,
            "Content-Type": "application/json"
        }
        servers = await get_project_servers(project_id, data, headers)
        print(f"完成获取项目 {project['name']} 的虚拟机: {len(servers)} 台")
        return project, servers

# 主函数
async def main():
    global auth_token, response_data,user_id
    auth_token, response_data, user_id = await get_auth_token()
    print(f"auth_token: {auth_token}")
    print(f"response_data: {response_data}")
    if not auth_token:
        print("认证失败，请检查用户名、密码或认证 URL")
        return

    # 获取所有项目
    all_projects = await get_projects()

    all_images = await get_images( response_data)

    pprint(all_images)


    print(f"总共项目数量: {len(all_projects)}")

    # 使用 Semaphore 控制并发任务数
    semaphore = asyncio.Semaphore(100)  # 限制并发任务数为 20

    # 使用 asyncio.gather 并发获取虚拟机
    tasks = [async_get_project_servers(project, semaphore) for project in all_projects]
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




    all_regions = await get_regions()
    print(f"总共区域数量: {len(all_regions)}")
    print(f"区域: {all_regions}")
    
    # all_domains = await get_domains()
    # print(f"总共域数量: {len(all_domains)}")
    # print(f"域: {all_domains}")

    print("获取到的所有项目信息:")
    for project in all_projects:
        print(f"project_id: {project['id']}, project_name: {project['name']}")




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