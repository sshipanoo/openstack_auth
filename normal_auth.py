import requests
from pprint import pprint
# OpenStack Keystone 认证 URL

base_url = "http://xxxxx/v3"

user_name = ""
password = ""
domain_name = "Default"





auth_url = f"{base_url}/auth/tokens"
projects_url = f"{base_url}/projects"


def get_auth_token():
    try:
        # 认证请求体
        auth_data ={
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": user_name,
                            "password": password,
                            "domain": {
                                "name": domain_name
                            }
                        }
                    }
                }
            }
        } 
        # 发送认证请求
        response = requests.post(auth_url, json=auth_data, headers={"Content-Type": "application/json"})
        # pprint(response.json())
        # 获取认证令牌
        token = response.headers["X-Subject-Token"]
        # print("Token:", token)
        return token,response.json()
    except Exception as e:
        print(e)
        return None,None        
    

def get_project_token(project_id):
    try:
        # 每个项目单独认证获取token
        # 认证请求体
        auth_data ={
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": user_name,
                            "password": password,
                            "domain": {
                                "name": domain_name
                            }
                        }
                    }
                },
                "scope": {
                    "project": {
                        "id": project_id,
                       
                    }
                }
            }
        } 


        # pprint(auth_data,indent=4)
        # 发送认证请求
        response = requests.post(auth_url, json=auth_data, headers={"Content-Type": "application/json"})
        
        # pprint(response.json())
        # 获取认证令牌

        token_key = 'X-Subject-Token'
        if token_key not in response.headers:
            token_key = token_key.lower()
        if token_key not in response.headers:
            # logger.error(f"not found token_key: {token_key}")
            return None,None

        token = response.headers[token_key]
        # print("Token:", token)
        return token,response.json()
    except Exception as e:
        print(e)
        print(response.text)
        return None,None

    


auth_token,response  = get_auth_token()


def get_nova_url(data):

    catalog = data.get('token').get('catalog')
    for cat in catalog:
        if cat.get('name') == 'nova' and cat.get('type') == 'compute':
            for endpoint in cat.get('endpoints'):
                print(endpoint)
                if endpoint.get('interface') == 'public':
                    url = endpoint.get('url')
                    # print(url)
                    # 返回去掉项目id的url
                    return "/".join(url.split("/")[:-1])




# 获取所有的项目信息
def get_projects():
    # OpenStack Keystone API URL
    # 发送请求

    # 请求头
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }   
    response = requests.get(projects_url, headers=headers)
    # print(response.text)
    # pprint(response.json())

    projects = response.json()['projects']
    return projects
   

# 获取所有的区域信息
def get_regions():
    # OpenStack Keystone API URL
    regions_url = f"{base_url}/regions"
    # 发送请求

    # 请求头
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }   
    response = requests.get(regions_url, headers=headers)
    # print(response.text)
    # pprint(response.json())

    regions = response.json()['regions']
    return regions

def get_domains():
    # OpenStack Keystone API URL
    domains_url = f"{base_url}/domains"
    # 发送请求

    # 请求头
    headers = {
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }   
    response = requests.get(domains_url, headers=headers)
    # print(response.text)
    # pprint(response.json())

    domains = response.json()['domains']
    return domains





def get_specific_project(project_id):

    print(f"获取指定项目信息({project_id}):")

    # OpenStack Keystone API URL
    # project_url = f"{projects_url}/{project_id}"

    project_token,data = get_project_token(project_id)
    if not project_token:
        print("获取指定项目token失败")
        return None
    headers = {
        "X-Auth-Token": project_token,
        "Content-Type": "application/json"
    }

    # # 发送请求
    # response = requests.get(project_url, headers=headers)
    # print(response.text)
    # pprint(response.json())

    # print(f"获取指定项目的服务器信息({project_id}):")
    return get_project_servers(project_id,data,headers=headers)


def get_project_servers(project_id,data,headers):
    # OpenStack Nova API URL

    nova_url = get_nova_url(data)

    server_url = f"{nova_url}/{project_id}/servers"
    # 发送请求
    response = requests.get(server_url, headers=headers)
    # print(response.text)
    # pprint(response.json())
    servers = response.json()['servers']
    return servers



if __name__ == "__main__":
    regions = get_regions()
    # print("regions:",regions)

    domains = get_domains()
    # print("domains:",domains)

    all_projects = get_projects()
    pprint(all_projects)
    

    ok_project_count = 0
    all_server_count = 0
    ok_project_names = []
    project_vms = []  # 用于存储每个项目的虚拟机信息

    for project in all_projects:
        print(f"project_id: {project['id']}, project_name: {project['name']}")
        
        # 获取当前项目下的虚拟机
        servers = get_specific_project(project['id'])
        
        if servers:
            ok_project_count += 1
            print(f"项目 {project['name']} 的服务器数量: {len(servers)}")
            ok_project_names.append(project['name'])
            all_server_count += len(servers)
            
            # 将当前项目的虚拟机信息存储到列表中
            for server in servers:
                project_vms.append({
                    "project_name": project['name'],
                    "vm_id": server['id'],
                    "vm_name": server['name'],
                })
        else:
            print(f"项目 {project['name']} 获取虚拟机失败")
        
        print("-------------------------------------")

    # 打印统计信息
    print("=====================================")

    print("获取到的所有项目信息:", all_projects)
    print("获取到的所有区域信息:", regions)
    print("获取到的所有域信息:", domains)

    print("总共项目数量:", len(all_projects))
    print("获取到 有虚拟机 的项目数量:", ok_project_count)
    print("获取到 有虚拟机的 的项目名称:", ok_project_names)
    print("获取到 虚拟机 的总数量:", all_server_count)

    # 打印所有项目的虚拟机信息（树状结构）
    print("\n所有项目的虚拟机信息:")
    current_project = None
    for index, vm in enumerate(project_vms):
        # 如果切换到新项目，打印项目名称
        if vm['project_name'] != current_project:
            current_project = vm['project_name']
            print(f"项目{current_project}")
        
        # 判断是否是当前项目的最后一个虚拟机
        is_last_vm = True
        if index < len(project_vms) - 1:
            next_vm = project_vms[index + 1]
            if next_vm['project_name'] == current_project:
                is_last_vm = False
        
        # 打印虚拟机信息
        if is_last_vm:
            print(f"└── 虚拟机 ID:{vm['vm_id']}  名称:{vm['vm_name']} ")
        else:
            print(f"├── 虚拟机 ID:{vm['vm_id']}  名称:{vm['vm_name']}")