import asyncio
import os
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage


@dataclass
class ClaudeCodeConfig:
    """Claude Code SDK 配置"""
    model: str = "claude-sonnet-4-20250514"
    system_prompt: str = "You are a helpful coding assistant."
    permission_mode: str = "acceptEdits"
    max_turns: int = 10
    allowed_tools: list[str] = field(default_factory=lambda: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"])
    agent_dir: str = ".claude_code"
    retries: int = 3
    
    def to_json(self) -> dict:
        """转换为 JSON 字典"""
        return asdict(self)


@dataclass
class ClaudeAgentResult:
    """Agent 执行结果"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    num_turns: int = 0
    duration_ms: int = 0


class ClaudeAgent:
    """使用 Claude Code SDK 执行代码生成任务的 Agent"""
    
    def __init__(self, config: ClaudeCodeConfig):
        """
        初始化 ClaudeAgent
        
        Args:
            config: ClaudeCodeConfig 配置对象
        """
        self.config = config
        self.model = config.model
        self.system_prompt = config.system_prompt
        self.permission_mode = config.permission_mode
        self.max_turns = config.max_turns
        self.allowed_tools = config.allowed_tools
        self.agent_dir = config.agent_dir
        self.retries = config.retries
        
    def _create_work_dir(self, task_uid: str) -> Path:
        """创建任务工作目录"""
        timestamp = int(time.time())
        work_dir = Path(self.agent_dir) / f"{timestamp}_{task_uid}"
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir
        
    async def _execute_task(
        self, 
        prompt: str, 
        work_dir: Path,
        target_file: str
    ) -> ClaudeAgentResult:
        """执行单次任务"""
        try:
            # 配置 ClaudeAgentOptions
            options = ClaudeAgentOptions(
                model=self.model,
                system_prompt=self.system_prompt,
                permission_mode=self.permission_mode,
                max_turns=self.max_turns,
                allowed_tools=self.allowed_tools,
                cwd=str(work_dir.absolute())
            )
            
            # 构建完整的 prompt，明确指定输出文件
            full_prompt = f"{prompt}\n\nIMPORTANT: Please write your final code to the file '{target_file}' in the current working directory."
            
            # 使用 ClaudeSDKClient 执行任务
            async with ClaudeSDKClient(options=options) as client:
                # 发送 prompt
                await client.query(full_prompt)
                
                # 接收响应
                result_info = None
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        # 处理助手消息（可选：记录日志）
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                print(f"Claude: {block.text[:100]}...")
                    elif isinstance(message, ResultMessage):
                        # 获取结果信息
                        result_info = message
                
                # 检查任务是否成功
                if result_info and not result_info.is_error:
                    # 读取目标文件
                    target_path = work_dir / target_file
                    if target_path.exists():
                        content = target_path.read_text(encoding='utf-8')
                        return ClaudeAgentResult(
                            success=True,
                            content=content,
                            num_turns=result_info.num_turns if result_info else 0,
                            duration_ms=result_info.duration_ms if result_info else 0
                        )
                    else:
                        return ClaudeAgentResult(
                            success=False,
                            error=f"Target file '{target_file}' not found in work directory"
                        )
                else:
                    error_msg = result_info.result if result_info else "Unknown error"
                    return ClaudeAgentResult(
                        success=False,
                        error=f"Task execution failed: {error_msg}"
                    )
                    
        except Exception as e:
            return ClaudeAgentResult(
                success=False,
                error=f"Exception during task execution: {str(e)}"
            )
    
    async def run(
        self, 
        prompt: str, 
        task_uid: str,
        target_file: str = "program.py"
    ) -> str:
        """
        执行任务并返回目标文件内容
        
        Args:
            prompt: 任务提示词
            task_uid: 任务唯一标识符
            target_file: 目标文件名（相对于工作目录）
            
        Returns:
            目标文件的内容
            
        Raises:
            RuntimeError: 任务执行失败且重试次数用尽
        """
        # 创建工作目录
        work_dir = self._create_work_dir(task_uid)
        print(f"Work directory: {work_dir.absolute()}")
        
        # 执行任务，支持重试
        last_error = None
        for attempt in range(self.retries):
            print(f"Attempt {attempt + 1}/{self.retries}...")
            
            result = await self._execute_task(prompt, work_dir, target_file)
            
            if result.success:
                print(f"Task completed successfully in {result.num_turns} turns ({result.duration_ms}ms)")
                return result.content
            else:
                last_error = result.error
                print(f"Attempt {attempt + 1} failed: {last_error}")
                
                if attempt < self.retries - 1:
                    # 等待后重试
                    await asyncio.sleep(1)
        
        # 所有重试都失败
        raise RuntimeError(f"Task failed after {self.retries} attempts. Last error: {last_error}")
