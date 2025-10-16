import paramiko
from pathlib import Path
from typing import Optional

class SSHConnectionManager:
    def __init__(self, ip_pool: list[str], key_path: str = "~/.ssh/id_rsa", port: int = 22, timeout_sec: int = 10):
        self.ip_pool = ip_pool
        self.key_path = Path(key_path).expanduser()
        self.port = port
        self.timeout_sec = timeout_sec
        self.connections: dict[str, paramiko.SSHClient] = {}
        self.private_key: Optional[paramiko.RSAKey] = None

    def execute_command(self, ip: str, command: str) -> tuple:
        """
        在指定主机上执行命令
        
        Args:
            ip: 目标 IP
            command: 要执行的命令
            
        Returns:
            (stdout, stderr, exit_code)
        """
        if ip not in self.connections:
            raise ValueError(f"未连接到主机: {ip}")
        
        client = self.connections[ip]
        stdin, stdout, stderr = client.exec_command(command)
        
        exit_code = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode('utf-8')
        stderr_text = stderr.read().decode('utf-8')
        
        return stdout_text, stderr_text, exit_code

    def __enter__(self):
        # 客户端建立与各个服务端之间的连接，准备好 evaluator 服务。
        print("开始建立 SSH 连接...")

        self._load_private_key()

        failed_connections = []
        for ip in self.ip_pool:
            try:
                client = self._connect_to_host(ip)
                self.connections[ip] = client
            except Exception as e:
                print(f"跳过无法连接的主机 {ip}: {e}")
                failed_connections.append(ip)
        if not self.connections:
            raise RuntimeError(f"所有主机连接失败：{self.ip_pool}")
        if failed_connections:
            print(f"以下主机连接失败：{failed_connections}")

        print(f"成功建立 {len(self.connections)} 个连接")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理资源
        print("开始清理 SSH 连接...")

        for ip, client in self.connections.items():
            try:
                client.close()
                print(f"已关闭连接: {ip}")
            except Exception as e:
                raise f"关闭连接 {ip} 时出错: {e}"

        self.connections.clear()
        print("所有连接已清理")

        # 不抑制异常
        return False

    def _load_private_key(self):
        """加载 SSH 私钥"""
        try:
            # 尝试加载 RSA 密钥
            self.private_key = paramiko.RSAKey.from_private_key_file(
                filename=str(self.key_path)
            )
            print(f"成功加载私钥: {self.key_path}")
        except paramiko.ssh_exception.PasswordRequiredException:
            raise "私钥需要密码，请使用无密码保护的密钥"
        except Exception as e:
            raise e

    def _connect_to_host(self, ip: str) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        # 自动添加主机密钥（生产环境建议使用已知的 host keys）
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # 使用密钥认证连接（无需用户名时，使用当前用户）
            client.connect(
                hostname=ip,
                port=self.port,
                pkey=self.private_key,
                timeout=self.timeout_sec,
                look_for_keys=False,  # 不自动查找其他密钥
                allow_agent=False     # 不使用 SSH agent
            )
            print(f"成功连接到 {ip}")
            return client
        except paramiko.AuthenticationException as e:
            print(f"连接 {ip} 认证失败")
            raise e
        except Exception as e:
            print(f"连接 {ip} 失败: {e}")
            raise e

    def execute_on_all(self, command: str) -> dict[str, tuple]:
        """
        在所有连接的主机上执行命令
        
        Args:
            command: 要执行的命令
            
        Returns:
            字典, key 为 IP, value 为 (stdout, stderr, exit_code)
        """
        results = {}
        for ip in self.connections:
            try:
                results[ip] = self.execute_command(ip, command)
            except Exception as e:
                print(f"在 {ip} 上执行命令失败: {e}")
                results[ip] = ("", str(e), -1)
        return results
