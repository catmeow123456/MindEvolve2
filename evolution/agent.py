import asyncio
import os
import time
import traceback
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from claude_agent_sdk import (
    ClaudeSDKClient, 
    ClaudeAgentOptions, 
    AssistantMessage, 
    TextBlock, 
    ResultMessage,
    ToolUseBlock,
    ToolResultBlock,
    UserMessage,
)


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
        self.debug_mode = os.getenv('DEBUG_MODE', 'FALSE').upper() == 'TRUE'
        
        self._debug_print("=" * 80)
        self._debug_print("ClaudeAgent 初始化")
        self._debug_print(f"模型: {self.model}")
        self._debug_print(f"系统提示词长度: {len(self.system_prompt)} 字符")
        self._debug_print(f"权限模式: {self.permission_mode}")
        self._debug_print(f"最大轮次: {self.max_turns}")
        self._debug_print(f"允许的工具: {', '.join(self.allowed_tools)}")
        self._debug_print(f"Agent 目录: {self.agent_dir}")
        self._debug_print(f"重试次数: {self.retries}")
        self._debug_print("-" * 80)
        self._debug_print("系统提示词完整内容:")
        self._debug_print(self.system_prompt)
        self._debug_print("=" * 80)
    
    def _debug_print(self, message: str, level: str = "INFO"):
        """
        打印调试信息
        
        Args:
            message: 调试消息
            level: 日志级别 (INFO, DEBUG, WARNING, ERROR)
        """
        if self.debug_mode:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] [{level}] {message}")
        
    def _create_work_dir(self, task_uid: str) -> Path:
        """创建任务工作目录"""
        timestamp = int(time.time())
        work_dir = Path(self.agent_dir) / f"{timestamp}_{task_uid}"
        
        self._debug_print("-" * 80)
        self._debug_print(f"创建工作目录: task_uid={task_uid}")
        self._debug_print(f"时间戳: {timestamp}")
        self._debug_print(f"目录路径: {work_dir.absolute()}")
        
        work_dir.mkdir(parents=True, exist_ok=True)
        
        self._debug_print(f"目录创建成功: {work_dir.exists()}")
        self._debug_print(f"目录权限: {oct(work_dir.stat().st_mode)[-3:]}")
        self._debug_print("-" * 80)
        
        return work_dir
        
    async def _execute_task(
        self, 
        prompt: str, 
        work_dir: Path,
        target_file: str
    ) -> ClaudeAgentResult:
        """执行单次任务"""
        try:
            self._debug_print("=" * 80)
            self._debug_print("开始执行任务")
            self._debug_print(f"工作目录: {work_dir.absolute()}")
            self._debug_print(f"目标文件: {target_file}")
            self._debug_print(f"原始提示词长度: {len(prompt)} 字符")
            
            # 配置 ClaudeAgentOptions
            options = ClaudeAgentOptions(
                model=self.model,
                system_prompt=self.system_prompt,
                permission_mode=self.permission_mode,
                max_turns=self.max_turns,
                allowed_tools=self.allowed_tools,
                cwd=str(work_dir.absolute())
            )
            
            self._debug_print("-" * 80)
            self._debug_print("ClaudeAgentOptions 配置:")
            self._debug_print(f"  - 模型: {options.model}")
            self._debug_print(f"  - 工作目录: {options.cwd}")
            self._debug_print(f"  - 权限模式: {options.permission_mode}")
            self._debug_print(f"  - 最大轮次: {options.max_turns}")
            self._debug_print(f"  - 允许的工具: {options.allowed_tools}")
            
            # 构建完整的 prompt，明确指定输出文件
            full_prompt = f"{prompt}\n\nIMPORTANT: Please write your final code to the file '{target_file}' in the current working directory."
            
            self._debug_print("-" * 80)
            self._debug_print("完整提示词:")
            self._debug_print(full_prompt)
            self._debug_print("-" * 80)
            
            # 使用 ClaudeSDKClient 执行任务
            async with ClaudeSDKClient(options=options) as client:
                self._debug_print("ClaudeSDKClient 已创建，开始发送查询...")
                
                # 发送 prompt
                await client.query(full_prompt)
                self._debug_print("查询已发送，等待响应...")
                
                # 接收响应
                result_info = None
                message_count = 0
                async for message in client.receive_response():
                    message_count += 1
                    self._debug_print(f"\n{'=' * 60}")
                    self._debug_print(f"收到消息 #{message_count}: {type(message).__name__}")
                    self._debug_print(f"{'=' * 60}")
                    
                    if isinstance(message, UserMessage):
                        # 用户消息
                        self._debug_print("  [USER MESSAGE]")
                        for idx, block in enumerate(message.content):
                            if isinstance(block, TextBlock):
                                self._debug_print(f"  UserMessage TextBlock #{idx + 1}:")
                                self._debug_print(f"    - 长度: {len(block.text)} 字符")
                                self._debug_print(f"    - 内容:")
                                self._debug_print(f"{block.text}")
                            elif isinstance(block, ToolResultBlock):
                                self._debug_print(f"  UserMessage ToolResultBlock #{idx + 1}:")
                                self._debug_print(f"    - tool_use_id: {block.tool_use_id}")
                                self._debug_print(f"    - 内容: {block.content}")
                                if hasattr(block, 'is_error'):
                                    self._debug_print(f"    - is_error: {block.is_error}")
                    
                    elif isinstance(message, AssistantMessage):
                        # 处理助手消息（可选：记录日志）
                        self._debug_print("  [ASSISTANT MESSAGE]")
                        for idx, block in enumerate(message.content):
                            if isinstance(block, TextBlock):
                                preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
                                print(f"Claude: {preview}")
                                
                                self._debug_print(f"  AssistantMessage TextBlock #{idx + 1}:")
                                self._debug_print(f"    - 长度: {len(block.text)} 字符")
                                self._debug_print(f"    - 完整内容:")
                                self._debug_print(f"{block.text}")
                            
                            elif isinstance(block, ToolUseBlock):
                                self._debug_print(f"  AssistantMessage ToolUseBlock #{idx + 1}:")
                                self._debug_print(f"    - id: {block.id}")
                                self._debug_print(f"    - 工具名称: {block.name}")
                                self._debug_print(f"    - 工具参数:")
                                # 格式化输出工具参数
                                import json
                                try:
                                    formatted_input = json.dumps(block.input, indent=2, ensure_ascii=False)
                                    self._debug_print(f"{formatted_input}")
                                except:
                                    self._debug_print(f"{block.input}")
                                
                                # 如果是 Bash 命令，特别标注
                                if block.name.lower() == 'bash':
                                    self._debug_print(f"    ⚡ [BASH 命令执行]")
                                    if 'command' in block.input:
                                        self._debug_print(f"    命令: {block.input['command']}")
                    
                    elif isinstance(message, ResultMessage):
                        # 获取结果信息
                        result_info = message
                        self._debug_print("  [RESULT MESSAGE]")
                        self._debug_print(f"    - is_error: {result_info.is_error}")
                        self._debug_print(f"    - num_turns: {result_info.num_turns}")
                        self._debug_print(f"    - duration_ms: {result_info.duration_ms}")
                        self._debug_print(f"    - result: {result_info.result}")
                    
                    else:
                        # 其他未知消息类型
                        self._debug_print(f"  [未知消息类型: {type(message).__name__}]")
                        self._debug_print(f"    - 消息内容: {message}")
                
                self._debug_print(f"总共收到 {message_count} 条消息")
                
                # 检查任务是否成功
                if result_info and not result_info.is_error:
                    self._debug_print("-" * 80)
                    self._debug_print("任务执行成功，检查目标文件...")
                    
                    # 读取目标文件
                    target_path = work_dir / target_file
                    self._debug_print(f"目标文件路径: {target_path.absolute()}")
                    self._debug_print(f"文件存在: {target_path.exists()}")
                    
                    if target_path.exists():
                        # 列出工作目录中的所有文件
                        self._debug_print("工作目录内容:")
                        for item in work_dir.iterdir():
                            self._debug_print(f"  - {item.name} ({'文件' if item.is_file() else '目录'})")
                        
                        content = target_path.read_text(encoding='utf-8')
                        self._debug_print(f"文件内容长度: {len(content)} 字符")
                        self._debug_print("文件内容预览（前200字符）:")
                        self._debug_print(content[:200])
                        self._debug_print("=" * 80)
                        
                        return ClaudeAgentResult(
                            success=True,
                            content=content,
                            num_turns=result_info.num_turns if result_info else 0,
                            duration_ms=result_info.duration_ms if result_info else 0
                        )
                    else:
                        # 列出工作目录中的所有文件以便调试
                        self._debug_print("工作目录内容:")
                        for item in work_dir.iterdir():
                            self._debug_print(f"  - {item.name}")
                        
                        error_msg = f"Target file '{target_file}' not found in work directory"
                        self._debug_print(f"错误: {error_msg}", "ERROR")
                        self._debug_print("=" * 80)
                        
                        return ClaudeAgentResult(
                            success=False,
                            error=error_msg
                        )
                else:
                    error_msg = result_info.result if result_info else "Unknown error"
                    self._debug_print(f"任务执行失败: {error_msg}", "ERROR")
                    self._debug_print("=" * 80)
                    
                    return ClaudeAgentResult(
                        success=False,
                        error=f"Task execution failed: {error_msg}"
                    )
                    
        except Exception as e:
            self._debug_print("=" * 80, "ERROR")
            self._debug_print(f"任务执行过程中发生异常: {str(e)}", "ERROR")
            self._debug_print("异常堆栈信息:", "ERROR")
            self._debug_print(traceback.format_exc(), "ERROR")
            self._debug_print("=" * 80, "ERROR")
            
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
            self._debug_print("=" * 80)
            self._debug_print(f"尝试 {attempt + 1}/{self.retries}")
            self._debug_print("=" * 80)
            
            result = await self._execute_task(prompt, work_dir, target_file)
            
            if result.success:
                print(f"Task completed successfully in {result.num_turns} turns ({result.duration_ms}ms)")
                self._debug_print("=" * 80)
                self._debug_print("✓ 任务成功完成!")
                self._debug_print(f"  - 轮次: {result.num_turns}")
                self._debug_print(f"  - 耗时: {result.duration_ms}ms")
                self._debug_print(f"  - 内容长度: {len(result.content)} 字符")
                self._debug_print("=" * 80)
                return result.content
            else:
                last_error = result.error
                print(f"Attempt {attempt + 1} failed: {last_error}")
                self._debug_print(f"✗ 尝试 {attempt + 1} 失败", "WARNING")
                self._debug_print(f"  错误信息: {last_error}", "WARNING")
                
                if attempt < self.retries - 1:
                    # 等待后重试
                    wait_time = 1
                    self._debug_print(f"等待 {wait_time} 秒后重试...", "WARNING")
                    await asyncio.sleep(wait_time)
        
        # 所有重试都失败
        self._debug_print("=" * 80, "ERROR")
        self._debug_print(f"✗ 任务失败：{self.retries} 次尝试均失败", "ERROR")
        self._debug_print(f"最后的错误: {last_error}", "ERROR")
        self._debug_print("=" * 80, "ERROR")
        
        raise RuntimeError(f"Task failed after {self.retries} attempts. Last error: {last_error}")
