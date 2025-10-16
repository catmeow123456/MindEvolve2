import asyncio
import pytest
from pathlib import Path
from evolution import ClaudeAgent, ClaudeCodeConfig
from evolution.config import CoreConfig


def test_claude_code_config_creation():
    """测试 ClaudeCodeConfig 的创建"""
    config = ClaudeCodeConfig(
        model="claude-sonnet-4-20250514",
        system_prompt="Test prompt",
        permission_mode="acceptEdits",
        max_turns=5,
        allowed_tools=["Read", "Write"],
        agent_dir=".test_claude_code",
        retries=2
    )
    
    assert config.model == "claude-sonnet-4-20250514"
    assert config.system_prompt == "Test prompt"
    assert config.permission_mode == "acceptEdits"
    assert config.max_turns == 5
    assert config.allowed_tools == ["Read", "Write"]
    assert config.agent_dir == ".test_claude_code"
    assert config.retries == 2
    
    # 测试 to_json
    json_dict = config.to_json()
    assert json_dict["model"] == "claude-sonnet-4-20250514"
    assert json_dict["max_turns"] == 5


def test_claude_agent_creation():
    """测试 ClaudeAgent 的创建"""
    config = ClaudeCodeConfig(
        model="claude-sonnet-4-20250514",
        system_prompt="Test prompt",
        max_turns=5
    )
    
    agent = ClaudeAgent(config)
    
    assert agent.model == "claude-sonnet-4-20250514"
    assert agent.system_prompt == "Test prompt"
    assert agent.max_turns == 5
    assert agent.retries == 3  # 默认值


def test_load_config_from_yaml():
    """测试从 YAML 加载 claude_code 配置"""
    config_path = Path("evolution/test/config_claude_code_example.yaml")
    
    if not config_path.exists():
        pytest.skip("Config file not found")
    
    core_config = CoreConfig.from_yaml(config_path)
    
    assert isinstance(core_config.llm, ClaudeCodeConfig)
    assert core_config.llm.model == "claude-sonnet-4-20250514"
    assert core_config.llm.system_prompt == "You are an expert Python programmer."
    assert core_config.llm.permission_mode == "acceptEdits"
    assert core_config.llm.max_turns == 15
    assert core_config.llm.retries == 3
    assert core_config.llm.agent_dir == ".claude_code"


@pytest.mark.asyncio
async def test_claude_agent_work_dir_creation():
    """测试工作目录创建"""
    config = ClaudeCodeConfig(
        agent_dir=".test_claude_agent",
        max_turns=1
    )
    
    agent = ClaudeAgent(config)
    task_uid = "test_task_001"
    
    # 创建工作目录
    work_dir = agent._create_work_dir(task_uid)
    
    assert work_dir.exists()
    assert work_dir.is_dir()
    assert task_uid in work_dir.name
    
    # 清理
    import shutil
    shutil.rmtree(".test_claude_agent", ignore_errors=True)


if __name__ == "__main__":
    # 运行基本测试
    test_claude_code_config_creation()
    print("✓ ClaudeCodeConfig creation test passed")
    
    test_claude_agent_creation()
    print("✓ ClaudeAgent creation test passed")
    
    test_load_config_from_yaml()
    print("✓ Load config from YAML test passed")
    
    asyncio.run(test_claude_agent_work_dir_creation())
    print("✓ Work directory creation test passed")
    
    print("\nAll tests passed!")
