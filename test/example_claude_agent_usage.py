"""
ClaudeAgent 使用示例

这个脚本展示了如何使用 ClaudeAgent 来生成代码。
"""

import asyncio
import dotenv
from evolution import ClaudeAgent, ClaudeCodeConfig

dotenv.load_dotenv()

async def example_simple_task():
    """简单任务示例：生成一个 Hello World 程序"""
    print("=" * 60)
    print("示例 1: 生成简单的 Hello World 程序")
    print("=" * 60)
    
    # 创建配置
    config = ClaudeCodeConfig(
        model="claude-sonnet-4-20250514",
        system_prompt="You are an expert Python programmer.",
        permission_mode="acceptEdits",
        max_turns=5,
        allowed_tools=["Read", "Write", "Edit"],
        agent_dir=".claude_code_examples",
        retries=2
    )
    
    # 创建 agent
    agent = ClaudeAgent(config)
    
    # 定义任务
    prompt = """
    Create a simple Python program that prints "Hello, World!" to the console.
    The program should be well-commented and follow Python best practices.
    """
    
    try:
        # 运行任务
        result = await agent.run(
            prompt=prompt,
            task_uid="hello_world_001",
            target_file="hello.py"
        )
        
        print("\n✓ 任务完成！生成的代码：")
        print("-" * 60)
        print(result)
        print("-" * 60)
        
    except Exception as e:
        print(f"\n✗ 任务失败: {e}")


async def example_data_processing():
    """数据处理示例：生成一个数据分析脚本"""
    print("\n" + "=" * 60)
    print("示例 2: 生成数据分析脚本")
    print("=" * 60)
    
    config = ClaudeCodeConfig(
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are an expert Python data scientist.",
        permission_mode="acceptEdits",
        max_turns=10,
        agent_dir=".claude_code_examples",
        retries=3
    )
    
    agent = ClaudeAgent(config)
    
    prompt = """
    Create a Python script that:
    1. Generates a random dataset with 100 samples
    2. Calculates basic statistics (mean, median, std)
    3. Prints the results in a formatted way
    
    Use numpy for numerical operations and include proper error handling.
    """
    
    try:
        result = await agent.run(
            prompt=prompt,
            task_uid="data_analysis_001",
            target_file="analysis.py"
        )
        
        print("\n✓ 任务完成！生成的代码：")
        print("-" * 60)
        print(result)
        print("-" * 60)
        
    except Exception as e:
        print(f"\n✗ 任务失败: {e}")


async def example_with_config_file():
    """使用配置文件的示例"""
    print("\n" + "=" * 60)
    print("示例 3: 从配置文件加载配置")
    print("=" * 60)
    
    from evolution.config import CoreConfig
    from pathlib import Path
    
    config_path = Path("evolution/test/config_claude_code_example.yaml")
    
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return
    
    # 从 YAML 加载配置
    core_config = CoreConfig.from_yaml(config_path)
    
    # 创建 agent
    agent = ClaudeAgent(core_config.llm)
    
    prompt = """
    Create a simple calculator program in Python with functions for:
    - Addition
    - Subtraction
    - Multiplication
    - Division (with zero division handling)
    
    Include a main function that demonstrates using all operations, test it to ensure it can run successfully.
    """
    
    try:
        result = await agent.run(
            prompt=prompt,
            task_uid="calculator_001",
            target_file="calculator.py"
        )
        
        print("\n✓ 任务完成！生成的代码：")
        print("-" * 60)
        print(result)
        print("-" * 60)
        
    except Exception as e:
        print(f"\n✗ 任务失败: {e}")


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("ClaudeAgent 使用示例")
    print("=" * 60)
    
    # 注意：这些示例需要安装并配置 Claude Code CLI
    # 由于这是演示代码，实际运行可能需要适当的环境设置
    
    # 选择要运行的示例（取消注释以运行）
    # await example_simple_task()
    # await example_data_processing()
    await example_with_config_file()
    
    print("\n提示：取消注释 main() 中的示例函数调用来运行具体示例")
    print("注意：需要确保 Claude Code CLI 已正确安装和配置")


if __name__ == "__main__":
    asyncio.run(main())
