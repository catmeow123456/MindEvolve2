from typing import Optional, Dict, Any
import uuid
import shutil
import os
import threading
import time
import json
import subprocess
from pathlib import Path
from .ssh import SSHConnectionManager
from utils.cache_manager import SimpleCacheManager

class RemoteEvaluatorServerManager(SSHConnectionManager):
    session_id: str
    source_dir: str
    target_dir: str
    available_ips: Optional[list[str]] = None
    cache: Optional[SimpleCacheManager]
    evaluation_config: dict[str, any]
    _occupied_ips: set[str]
    _lock: threading.Lock

    def __init__(
        self,
        source_dir: str,
        output_dir: str,
        ip_pool: list[str],
        key_path: str = "~/.ssh/id_rsa",
        port: int = 22,
        timeout_sec: int = 10,
        cache: Optional[SimpleCacheManager] = None,
        evaluation_config: Optional[dict[str, any]] = None
    ):
        super().__init__(ip_pool, key_path, port, timeout_sec)
        self.session_id = str(uuid.uuid4())
        self.source_dir = source_dir
        self.target_dir = os.path.join(output_dir, self.session_id)
        self.cache = cache
        self.evaluation_config = evaluation_config or {}
        self._occupied_ips = set()
        self._lock = threading.Lock()

    def __enter__(self):
        super().__enter__()
        
        # 同步必要的文件到远程
        shutil.copytree("api", os.path.join(self.target_dir, "api"))
        shutil.copytree("core/base", os.path.join(self.target_dir, "core/base"))
        shutil.copytree(self.source_dir, os.path.join(self.target_dir, "core/task"))
        shutil.copy2("core/__init__.py", os.path.join(self.target_dir, "core/__init__.py"))
        shutil.copy2(".python-version", os.path.join(self.target_dir, ".python-version"))
        shutil.copy2("pyproject.toml", os.path.join(self.target_dir, "pyproject.toml"))
        shutil.copy2("evaluator_worker.py", os.path.join(self.target_dir, "evaluator_worker.py"))
        shutil.copy2(".env", os.path.join(self.target_dir, ".env"))
        
        # 创建任务目录
        os.makedirs(os.path.join(self.target_dir, "tasks"), exist_ok=True)

        # 安装依赖（共享存储，只需在本地执行）
        command = f"cd {os.path.abspath(self.target_dir)} && uv sync"
        print(f"执行命令: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"exit_code={result.returncode}")
        if result.returncode != 0:
            print(f"stderr: {result.stderr}")
            raise RuntimeError(f"依赖安装失败: {result.stderr}")

        self.available_ips = list(self.connections.keys())
        print(f"可用节点: {self.available_ips}")
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理所有评估任务的 tmux 会话（可选）
        # 注意：由于每个任务使用独立的 tmux 会话，这里可以选择保留用于调试
        print("清理资源...")
        super().__exit__(exc_type, exc_val, exc_tb)
        return False

    def start_tmux_session(
        self, 
        session_name: str, 
        command: str, 
        working_dir: str = None,
        log_file: str = None,
        ip: Optional[str] = None
    ) -> dict[str, tuple]:
        """
        在指定主机或所有主机上使用 tmux 启动后台程序
        
        Args:
            session_name: tmux 会话名称
            command: 要执行的命令
            working_dir: 工作目录（可选）
            log_file: 日志文件路径（可选）
            ip: 目标主机 IP（可选），如果指定则只在该主机执行，否则在所有主机执行
            
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

        # 根据是否指定 ip 来选择执行方式
        if ip:
            stdout, stderr, exit_code = self.execute_command(ip, full_command)
            return {ip: (stdout, stderr, exit_code)}
        else:
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

    def check_evaluation_result(self, output_file: str) -> Dict[str, Any]:
        """
        检查评估任务结果
        
        Args:
            output_file: 结果文件路径
            
        Returns:
            结果字典，包含 'completed' 字段指示是否完成
        """
        result = {'completed': False, 'success': False, 'result': None, 'metadata': None, 'error': None}
        
        try:
            output_path = Path(output_file)
            if output_path.exists():
                # 读取结果文件
                content = output_path.read_text(encoding='utf-8')
                data = json.loads(content)
                
                result['completed'] = True
                result['success'] = data.get('success', False)
                result['result'] = data.get('result')
                result['metadata'] = data.get('metadata')
                result['error'] = data.get('error')
                
        except json.JSONDecodeError as e:
            result['completed'] = False
            result['error'] = f"结果文件格式错误: {str(e)}"
        except Exception as e:
            result['completed'] = False
            result['error'] = f"读取结果文件异常: {str(e)}"
            
        return result

    def wait_for_result(self, output_file: str, timeout_sec: int, poll_interval: float = 1.0) -> Dict[str, Any]:
        """
        轮询等待评估结果
        
        Args:
            output_file: 结果文件路径
            timeout_sec: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
            
        Returns:
            评估结果字典
        """
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            # 检查是否超时
            if elapsed >= timeout_sec:
                return {
                    'completed': False,
                    'success': False,
                    'result': None,
                    'metadata': None,
                    'error': f'评估超时（{timeout_sec}秒）'
                }
            
            # 检查结果
            result = self.check_evaluation_result(output_file)
            if result['completed']:
                return result
            
            # 等待后继续轮询
            time.sleep(poll_interval)

    def execute_evaluation(self, ip: str, code: str, timeout_sec: int = 30) -> Dict[str, Any]:
        """
        在指定节点执行评估并等待结果
        
        Args:
            ip: 目标节点 IP
            code: 待评估的代码
            timeout_sec: 超时时间（秒）
            
        Returns:
            评估结果字典
        """
        # 检查缓存
        if self.cache is not None:
            cache_params = {"code": code, **self.evaluation_config}
            cached_response = self.cache.get_cached_response(**cache_params)
            if cached_response:
                return json.loads(cached_response)
        
        # 生成任务 ID
        task_id = str(uuid.uuid4())
        
        # 定义文件路径
        target_dir_abs = os.path.abspath(self.target_dir)
        tasks_dir = os.path.join(target_dir_abs, "tasks")
        code_file = os.path.join(tasks_dir, f"{task_id}_code.py")
        output_file = os.path.join(tasks_dir, f"{task_id}_result.json")
        
        try:
            # 写入代码文件到本地
            Path(code_file).write_text(code, encoding='utf-8')
            
            # 构建评估命令
            eval_command = f"uv run evaluator_worker.py --code-file {code_file} --output-file {output_file}"
            
            # 在 tmux 会话中执行（指定 ip）
            session_name = f"eval-{task_id}"
            tmux_results = self.start_tmux_session(
                session_name=session_name,
                command=eval_command,
                working_dir=target_dir_abs,
                ip=ip
            )
            
            # 检查是否成功启动
            if ip not in tmux_results:
                result = {
                    'success': False,
                    'result': None,
                    'metadata': None,
                    'error': f"节点 {ip} 未返回结果",
                    'ip': ip
                }
                if self.cache is not None:
                    self.cache.cache_response(response=json.dumps(result), **cache_params)
                return result
            
            stdout, stderr, exit_code = tmux_results[ip]
            if exit_code != 0:
                result = {
                    'success': False,
                    'result': None,
                    'metadata': None,
                    'error': f"tmux 启动失败: exit_code={exit_code}, stderr={stderr}",
                    'ip': ip
                }
                if self.cache is not None:
                    self.cache.cache_response(response=json.dumps(result), **cache_params)
                return result
            
            # 等待结果
            eval_result = self.wait_for_result(output_file, timeout_sec, poll_interval=1.0)
            
            # 添加 IP 信息
            eval_result['ip'] = ip
            
            # 缓存结果
            if self.cache is not None and eval_result['completed']:
                self.cache.cache_response(response=json.dumps(eval_result), **cache_params)
            
            return eval_result
            
        except Exception as e:
            result = {
                'success': False,
                'result': None,
                'metadata': None,
                'error': f"提交任务异常: {str(e)}",
                'ip': ip
            }
            if self.cache is not None:
                self.cache.cache_response(response=json.dumps(result), **cache_params)
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

    def execute_evaluation_auto(self, code: str, timeout_sec: int = 30, wait_timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        自动选择可用 IP 并执行评估，同一时间一个 IP 只能被一个请求占用
        
        Args:
            code: 待评估的代码
            timeout_sec: 评估超时时间（秒）
            wait_timeout: 等待可用 IP 的超时时间（秒），None 表示无限等待
            
        Returns:
            评估结果字典
        """
        ip = self.acquire_ip(wait_timeout)
        if not ip:
            return {
                'success': False,
                'result': None,
                'metadata': None,
                'ip': None,
                'error': '无法获取可用 IP'
            }
        
        try:
            result = self.execute_evaluation(ip, code, timeout_sec)
            return result
        finally:
            self._release_ip(ip)

    def get_resource_status(self) -> Dict[str, Any]:
        """获取资源使用状态"""
        with self._lock:
            if not self.available_ips:
                return {
                    'total': 0,
                    'occupied': 0,
                    'available': 0,
                    'occupied_ips': [],
                    'available_ips': []
                }
            total = len(self.available_ips)
            occupied = len(self._occupied_ips)
            return {
                'total': total,
                'occupied': occupied,
                'available': total - occupied,
                'occupied_ips': list(self._occupied_ips),
                'available_ips': [ip for ip in self.available_ips if ip not in self._occupied_ips]
            }
