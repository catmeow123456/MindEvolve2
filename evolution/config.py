from dataclasses import dataclass, field
from api import OpenAIConfig, AnthropicConfig, LiteLLMConfig
from evolution.agent import ClaudeCodeConfig
from core.base import TaskEvaluator
from pathlib import Path
from typing import Union, Optional
import yaml
from dacite import from_dict, Config

@dataclass
class EvolutionSettingConfig:
    """Configuration for evolution setting"""
    max_iterations: int = 100
    program_pool_size: int = 10

@dataclass
class CacheConfig:
    enabled: bool = False
    cache_dir: Optional[str] = None

@dataclass
class CoreConfig:
    output_dir: str = "output"
    task_name: str = "default"
    llm: Union[OpenAIConfig, AnthropicConfig, LiteLLMConfig, ClaudeCodeConfig] = field(default_factory=OpenAIConfig)
    evolution_setting: EvolutionSettingConfig = field(default_factory=EvolutionSettingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    evaluation_timeout_sec: int = 1000
    seed: Optional[int] = None

    @classmethod
    def from_yaml(cls, path: Union[str, Path]):
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)
        
        # 处理 llm 配置：根据 provider 字段选择正确的配置类
        if "llm" in config_dict and isinstance(config_dict["llm"], dict):
            llm_config = config_dict["llm"]
            provider = llm_config.pop("provider", "openai")  # 默认为 openai
            
            # 根据 provider 选择对应的配置类
            if provider == "openai":
                config_dict["llm"] = from_dict(data_class=OpenAIConfig, data=llm_config, config=Config(strict=True, check_types=True))
            elif provider == "anthropic":
                config_dict["llm"] = from_dict(data_class=AnthropicConfig, data=llm_config, config=Config(strict=True, check_types=True))
            elif provider == "litellm":
                config_dict["llm"] = from_dict(data_class=LiteLLMConfig, data=llm_config, config=Config(strict=True, check_types=True))
            elif provider == "claude_code":
                config_dict["llm"] = from_dict(data_class=ClaudeCodeConfig, data=llm_config, config=Config(strict=True, check_types=True))
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}. Supported providers: openai, anthropic, litellm, claude_code")
        
        # 使用 dacite 处理其他字段
        return from_dict(data_class=cls, data=config_dict, config=Config(strict=True, check_types=True))
