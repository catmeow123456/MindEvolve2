from evolution.ssh import SSHConnectionManager

ssh_connection_manager = SSHConnectionManager(
    ip_pool=["cnkunpeng04"],
    key_path="~/.ssh/id_rsa",
)

with ssh_connection_manager as manager:
    manager.execute_command("cnkunpeng04", "touch ~/tmp.txt")
    manager.execute_command("cnkunpeng04", "echo \"Hello World\" > ~/tmp.txt")
