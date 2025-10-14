from typing import Tuple, Optional, Dict, Any
import uuid
import shutil
import os
import threading
import time
import requests
import json
from .ssh import SSHConnectionManager
from utils.cache_manager import SimpleCacheManager

class RemoteEvaluatorServerManager(SSHConnectionManager):
    session_id: str
    source_dir: str
    target_dir: str
    available_ips: Optional[list[str]] = None
    request_port: int
    cache: Optional[SimpleCacheManager]
    _occupied_ips: set[str]
    _lock: threading.Lock

    def __init__(
        self,
        source_dir: str,
        output_dir: str,
        ip_pool: list[str],
        key_path: str = "~/.ssh/id_rsa",
        port: int = 22,
        request_port: int = 9000,
        timeout: int = 10,
        cache: Optional[SimpleCacheManager] = None
    ):
        super().__init__(ip_pool, key_path, port, timeout)
        self.session_id = str(uuid.uuid4())
        self.source_dir = source_dir
        self.target_dir = os.path.join(output_dir, self.session_id)
        self.request_port = request_port
        self.cache = cache
        self._occupied_ips = set()
        self._lock = threading.Lock()

    def __enter__(self):
        super().__enter__()
        shutil.copytree("api", os.path.join(self.target_dir, "api"))
        shutil.copytree("core/base", os.path.join(self.target_dir, "core/base"))
        shutil.copytree(self.source_dir, os.path.join(self.target_dir, "core/task"))
        shutil.copy2("core/__init__.py", os.path.join(self.target_dir, "core/__init__.py"))
        shutil.copy2(".python-version", os.path.join(self.target_dir, ".python-version"), )
        shutil.copy2("pyproject.toml", os.path.join(self.target_dir, "pyproject.toml"))
        shutil.copy2("server.py", os.path.join(self.target_dir, "server.py"))
        shutil.copy2(".env", os.path.join(self.target_dir, ".env"))

        command1 = f"cd {os.path.abspath(self.target_dir)} && uv sync"
        results: dict[str, tuple] = self.execute_on_all(command1)
        print(f"Command `{command1}` result:")
        for ip, (stdout, stderr, exit_code) in results.items():
            print(f"{ip}: exit_code={exit_code}")

        results = self.start_tmux_session(
            "mindevolve-server",
            "export $(grep -v \"^#\" .env | xargs) && uv run server.py",
            working_dir=os.path.abspath(self.target_dir)
        )
        self.available_ips = []
        print(f"Result:")
        for ip, (stdout, stderr, exit_code) in results.items():
            print(f"{ip}: exit_code={exit_code}")
            self.available_ips.append(ip)
        try:
            print("等待全部服务启动... 按 Ctrl+C 退出")
            while True:
                time.sleep(1)
                # {'success': True, 'status_code': 200, 'error': None, 'data': {'message': 'Service is running normally', 'status': 'healthy'}}
                if all([self.check_health(ip, self.request_port)['success'] for ip in self.available_ips]):
                    break
            print("全部服务启动完毕!")
        except KeyboardInterrupt:
            print("\n检测到 Ctrl+C，正在退出程序...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for ip in self.available_ips:
            # {'success': True, 'status_code': 200, 'error': None, 'data': {'message': 'Shutdown request sent (connection closed as expected)'}}
            response = self.send_shutdown_request(ip, self.request_port, timeout=5)
            if response['success']:
                print(f"{ip} 服务关闭成功")
            else:
                print(f"{ip} 服务关闭失败: error = {response['error']}, data = {response['data']}")
        self.kill_tmux_session("mindevolve-server")
        super().__exit__(exc_type, exc_val, exc_tb)
        return False

    def start_tmux_session(
        self, 
        session_name: str, 
        command: str, 
        working_dir: str = None,
        log_file: str = None
    ) -> dict[str, tuple]:
        """
        在所有主机上使用 tmux 启动后台程序
        
        Args:
            session_name: tmux 会话名称
            command: 要执行的命令
            working_dir: 工作目录（可选）
            log_file: 日志文件路径（可选）
            
        Returns:
            执行结果字典
        """
        # 构建完整命令
        cmd_parts = []

        # 先杀掉可能存在的同名会话
        cmd_parts.append(f"tmux kill-session -t {session_name} 2>/dev/null || true")

        # 构建 tmux 命令
        tmux_cmd = f"tmux new-session -d -s {session_name}"

        # 构建要在 tmux 中执行的命令
        inner_cmd_parts = []
        if working_dir:
            inner_cmd_parts.append(f"cd {working_dir}")
        inner_cmd_parts.append(command)

        inner_cmd = " && ".join(inner_cmd_parts)

        # 添加日志重定向
        if log_file:
            inner_cmd += f" > {log_file} 2>&1"

        cmd_parts.append(f"{tmux_cmd} '{inner_cmd}'")

        full_command = " && ".join(cmd_parts)
        print("Full Command:", full_command)

        return self.execute_on_all(full_command)
    
    def check_tmux_session(self, session_name: str) -> dict[str, bool]:
        """检查 tmux 会话是否存在"""
        command = f"tmux has-session -t {session_name} 2>/dev/null && echo 'exists' || echo 'not_exists'"
        results = self.execute_on_all(command)
        
        status = {}
        for ip, (stdout, stderr, exit_code) in results.items():
            status[ip] = stdout.strip() == 'exists'
        return status
    
    def list_tmux_sessions(self) -> dict[str, list[str]]:
        """列出所有 tmux 会话"""
        command = "tmux list-sessions 2>/dev/null || echo 'no sessions'"
        results = self.execute_on_all(command)
        
        sessions = {}
        for ip, (stdout, stderr, exit_code) in results.items():
            if stdout.strip() != 'no sessions':
                sessions[ip] = stdout.strip().split('\n')
            else:
                sessions[ip] = []
        return sessions
    
    def kill_tmux_session(self, session_name: str) -> dict[str, tuple]:
        """终止指定的 tmux 会话"""
        command = f"tmux kill-session -t {session_name}"
        return self.execute_on_all(command)

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """统一的 HTTP 请求处理"""
        result = {'success': False, 'status_code': None, 'error': None}
        try:
            response = getattr(requests, method)(url, **kwargs)
            result['status_code'] = response.status_code
            result['success'] = response.status_code == 200
            return result, response
        except requests.exceptions.Timeout:
            result['error'] = f"请求超时：{url}"
        except requests.exceptions.ConnectionError:
            result['error'] = f"连接错误：{url}"
        except Exception as e:
            result['error'] = f"请求异常：{str(e)}"
        return result, None

    def check_health(self, ip: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """检查服务健康状态"""
        result, response = self._make_request('get', f"http://{ip}:{port}/health", timeout=timeout)
        if response:
            result['data'] = response.json()
        return result

    def send_evaluate_request(self, ip: str, code: str, port: int, timeout: int = 30) -> Dict[str, Any]:
        """发送代码评估请求"""
        if self.cache is not None:
            cache_params = {"code": code}
            cached_response = self.cache.get_cached_response(**cache_params)
            if cached_response:
                return json.loads(cached_response)
        result, response = self._make_request(
            'post', 
            f"http://{ip}:{port}/evaluate",
            json={'code': code},
            headers={'Content-Type': 'application/json'},
            timeout=timeout
        )
        result.update({'result': None, 'metadata': None})
        if response and response.status_code == 200:
            data = response.json()
            result['result'] = data.get('result')
            result['metadata'] = data.get('metadata')
        elif response:
            result['error'] = f"状态码 {response.status_code}：{response.text}"
        if self.cache is not None:
            self.cache.cache_response(response=json.dumps(result), **cache_params)
        return result

    def send_shutdown_request(self, ip: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """发送服务关闭请求"""
        result = {'success': False, 'status_code': None, 'error': None, 'data': None}
        try:
            response = requests.post(f"http://{ip}:{port}/shutdown", timeout=timeout)
            result['status_code'] = response.status_code
            result['success'] = response.status_code == 200
            result['data'] = response.json()
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError) as e:
            # 服务器关闭导致的连接断开是预期行为
            if 'IncompleteRead' in str(e) or 'Connection broken' in str(e):
                result['success'] = True
                result['status_code'] = 200
                result['data'] = {'message': 'Shutdown request sent (connection closed as expected)'}
            else:
                result['error'] = f"连接错误：{str(e)}"
        except requests.exceptions.Timeout:
            result['error'] = f"请求超时"
        except Exception as e:
            result['error'] = f"请求异常：{str(e)}"
        return result

    def acquire_ip(self, wait_timeout: Optional[float] = None) -> Optional[str]:
        """获取可用 IP，每个 IP 同一时间只能被一个请求占用"""
        start_time = time.time()
        while True:
            with self._lock:
                if self.available_ips:
                    for ip in self.available_ips:
                        if ip not in self._occupied_ips:
                            self._occupied_ips.add(ip)
                            return ip
            if wait_timeout and time.time() - start_time >= wait_timeout:
                return None
            time.sleep(0.1)

    def _release_ip(self, ip: str) -> None:
        """释放 IP 资源"""
        with self._lock:
            self._occupied_ips.discard(ip)

    def send_evaluate_request_auto(self, code: str, port: int,
                                   request_timeout: int = 30, wait_timeout: Optional[float] = None) -> Dict[str, Any]:
        """自动选择可用 IP 并发送评估请求，同一时间一个 IP 只能被一个请求占用"""
        ip = self.acquire_ip(wait_timeout)
        if not ip:
            return {'success': False, 'status_code': None, 'result': None, 
                   'metadata': None, 'ip': None, 'error': '无法获取可用 IP'}
        try:
            result = self.send_evaluate_request(ip, code, port, request_timeout)
            result['ip'] = ip
            return result
        finally:
            self._release_ip(ip)

    def get_resource_status(self) -> Dict[str, Any]:
        """获取资源使用状态"""
        with self._lock:
            if not self.available_ips:
                return {'total': 0, 'occupied': 0, 'available': 0, 'occupied_ips': [], 'available_ips': []}
            total = len(self.available_ips)
            occupied = len(self._occupied_ips)
            return {
                'total': total,
                'occupied': occupied,
                'available': total - occupied,
                'occupied_ips': list(self._occupied_ips),
                'available_ips': [ip for ip in self.available_ips if ip not in self._occupied_ips]
            }
