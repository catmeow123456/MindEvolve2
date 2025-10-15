"""
测试 EvolutionEngine 对不同 LLM provider 的支持
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evolution.config import CoreConfig
from evolution.main import EvolutionEngine
from api import AsyncOpenAILLM, AsyncAnthropicLLM, AsyncLiteLLM


def create_mock_task_plugin():
    """创建一个模拟的 TaskPlugin"""
    mock_plugin = MagicMock()
    mock_plugin.task_path = "mock/path"
    mock_plugin.get_task_name.return_value = "mock_task"
    mock_plugin.create_evaluator.return_value = MagicMock()
    mock_plugin.get_evaluation_config.return_value = {}
    return mock_plugin


def test_openai_llm_creation():
    """测试 OpenAI LLM 实例创建"""
    print("测试 OpenAI LLM 实例创建...")
    
    # 设置环境变量
    os.environ["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
    os.environ["OPENAI_API_KEY"] = "test_key"
    
    config = CoreConfig.from_yaml("evolution/test/config_openai_example.yaml")
    mock_plugin = create_mock_task_plugin()
    
    engine = EvolutionEngine(mock_plugin, config)
    
    assert isinstance(engine.llm, AsyncOpenAILLM), f"Expected AsyncOpenAILLM, got {type(engine.llm)}"
    assert engine.llm.config.model == "o3-2025-04-16"
    assert engine.llm.config.reasoning_effort == "high"
    
    print("✓ OpenAI LLM 实例创建成功")
    print(f"  LLM 类型: {type(engine.llm).__name__}")
    print(f"  模型: {engine.llm.config.model}")
    print()


def test_anthropic_llm_creation():
    """测试 Anthropic LLM 实例创建"""
    print("测试 Anthropic LLM 实例创建...")
    
    # 设置环境变量
    os.environ["ANTHROPIC_API_KEY"] = "test_key"
    
    config = CoreConfig.from_yaml("evolution/test/config_anthropic_example.yaml")
    mock_plugin = create_mock_task_plugin()
    
    engine = EvolutionEngine(mock_plugin, config)
    
    assert isinstance(engine.llm, AsyncAnthropicLLM), f"Expected AsyncAnthropicLLM, got {type(engine.llm)}"
    assert engine.llm.config.model == "claude-sonnet-4-5-20250929"
    assert engine.llm.config.thinking_enabled == True
    
    print("✓ Anthropic LLM 实例创建成功")
    print(f"  LLM 类型: {type(engine.llm).__name__}")
    print(f"  模型: {engine.llm.config.model}")
    print()


def test_litellm_llm_creation():
    """测试 LiteLLM LLM 实例创建"""
    print("测试 LiteLLM LLM 实例创建...")
    
    # 设置环境变量（LiteLLM 可以从环境变量读取）
    os.environ["OPENAI_API_KEY"] = "test_key"
    
    config = CoreConfig.from_yaml("evolution/test/config_litellm_example.yaml")
    mock_plugin = create_mock_task_plugin()
    
    engine = EvolutionEngine(mock_plugin, config)
    
    assert isinstance(engine.llm, AsyncLiteLLM), f"Expected AsyncLiteLLM, got {type(engine.llm)}"
    assert engine.llm.config.model == "gemini/gemini-2.5-flash"
    
    print("✓ LiteLLM LLM 实例创建成功")
    print(f"  LLM 类型: {type(engine.llm).__name__}")
    print(f"  模型: {engine.llm.config.model}")
    print()


def test_existing_config_compatibility():
    """测试现有配置文件的兼容性"""
    print("测试现有配置文件兼容性...")
    
    os.environ["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
    os.environ["OPENAI_API_KEY"] = "test_key"
    
    config = CoreConfig.from_yaml("evolution/test/config.yaml")
    mock_plugin = create_mock_task_plugin()
    
    engine = EvolutionEngine(mock_plugin, config)
    
    assert isinstance(engine.llm, AsyncOpenAILLM), f"Expected AsyncOpenAILLM, got {type(engine.llm)}"
    assert engine.llm.config.model == "deepseek-v3-250324"
    
    print("✓ 现有配置文件兼容性测试通过")
    print(f"  LLM 类型: {type(engine.llm).__name__}")
    print(f"  模型: {engine.llm.config.model}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试 EvolutionEngine LLM 实例化")
    print("=" * 60)
    print()
    
    try:
        test_openai_llm_creation()
        test_anthropic_llm_creation()
        test_litellm_llm_creation()
        test_existing_config_compatibility()
        
        print("=" * 60)
        print("所有测试通过！✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
