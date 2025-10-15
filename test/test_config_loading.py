"""
测试不同 LLM provider 的配置加载
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evolution.config import CoreConfig
from api import OpenAIConfig, AnthropicConfig, LiteLLMConfig


def test_openai_config():
    """测试 OpenAI 配置加载"""
    print("测试 OpenAI 配置...")
    config = CoreConfig.from_yaml("evolution/test/config_openai_example.yaml")
    assert isinstance(config.llm, OpenAIConfig), f"Expected OpenAIConfig, got {type(config.llm)}"
    assert config.llm.model == "o3-2025-04-16"
    assert config.llm.reasoning_effort == "high"
    print("✓ OpenAI 配置加载成功")
    print(f"  模型: {config.llm.model}")
    print(f"  推理努力: {config.llm.reasoning_effort}")
    print()


def test_anthropic_config():
    """测试 Anthropic 配置加载"""
    print("测试 Anthropic 配置...")
    config = CoreConfig.from_yaml("evolution/test/config_anthropic_example.yaml")
    assert isinstance(config.llm, AnthropicConfig), f"Expected AnthropicConfig, got {type(config.llm)}"
    assert config.llm.model == "claude-sonnet-4-5-20250929"
    assert config.llm.thinking_enabled == True
    assert config.llm.thinking_budget_tokens == 1024
    print("✓ Anthropic 配置加载成功")
    print(f"  模型: {config.llm.model}")
    print(f"  启用思考: {config.llm.thinking_enabled}")
    print(f"  思考令牌预算: {config.llm.thinking_budget_tokens}")
    print()


def test_litellm_config():
    """测试 LiteLLM 配置加载"""
    print("测试 LiteLLM 配置...")
    config = CoreConfig.from_yaml("evolution/test/config_litellm_example.yaml")
    assert isinstance(config.llm, LiteLLMConfig), f"Expected LiteLLMConfig, got {type(config.llm)}"
    assert config.llm.model == "gemini/gemini-2.5-flash"
    print("✓ LiteLLM 配置加载成功")
    print(f"  模型: {config.llm.model}")
    print()


def test_existing_config():
    """测试现有配置文件（向后兼容）"""
    print("测试现有配置文件（向后兼容）...")
    config = CoreConfig.from_yaml("evolution/test/config.yaml")
    assert isinstance(config.llm, OpenAIConfig), f"Expected OpenAIConfig, got {type(config.llm)}"
    assert config.llm.model == "deepseek-v3-250324"
    print("✓ 现有配置文件加载成功")
    print(f"  模型: {config.llm.model}")
    print()


def test_default_provider():
    """测试默认 provider（不指定时应该默认为 openai）"""
    print("测试默认 provider...")
    # 创建一个临时配置来测试
    import yaml
    import tempfile
    
    test_config = {
        "task_name": "test",
        "llm": {
            # 不指定 provider，应该默认为 openai
            "model": "gpt-4",
            "max_tokens": 1000
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_path = f.name
    
    try:
        config = CoreConfig.from_yaml(temp_path)
        assert isinstance(config.llm, OpenAIConfig), f"Expected OpenAIConfig (default), got {type(config.llm)}"
        print("✓ 默认 provider 测试通过（默认为 openai）")
        print()
    finally:
        Path(temp_path).unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试 LLM 配置加载功能")
    print("=" * 60)
    print()
    
    try:
        test_openai_config()
        test_anthropic_config()
        test_litellm_config()
        test_existing_config()
        test_default_provider()
        
        print("=" * 60)
        print("所有测试通过！✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
