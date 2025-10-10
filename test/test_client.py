import os
from dotenv import load_dotenv
from evolution.client import RemoteEvaluatorServerManager

load_dotenv()
# 环境变量的例子
#   HOSTNAME_LIST=cnkunpeng04;cnkunpeng05;cnkunpeng06;cnkunpeng07
# 从环境变量读取主机列表并转换为列表

hostname_list = os.environ.get('HOSTNAME_LIST', '')
ip_pool = [ip.strip() for ip in hostname_list.split(';') if ip.strip()]
print(ip_pool)

client = RemoteEvaluatorServerManager(
    source_dir="core/dictator_game",
    output_dir="output",
    ip_pool=ip_pool,
    key_path="~/.ssh/id_rsa",
)

with client as manager:
    print('Available IPs', manager.available_ips)
    
    status = manager.check_tmux_session("mindevolve-server")
    for ip, exists in status.items():
        print(f"{ip}: 会话存在={exists}")

    sessions = manager.list_tmux_sessions()
    for ip, session_list in sessions.items():
        print(f"{ip}: {session_list}")

    print(manager.get_resource_status())
