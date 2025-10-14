from dataclasses import dataclass, field
from api import OpenAIConfig
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
    llm: OpenAIConfig = field(default_factory=OpenAIConfig)
    evolution_setting: EvolutionSettingConfig = field(default_factory=EvolutionSettingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    evaluation_timeout: int = 1000

    @classmethod
    def from_yaml(cls, path: Union[str, Path]):
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)
        return from_dict(data_class=cls, data=config_dict, config=Config(strict=True, check_types=True))
