import os
import yaml
from typing import Union, Any
from dataclasses import dataclass, field
from pathlib import Path
from dacite import from_dict, Config

@dataclass
class TaskConfig:
    name: str
    plugin_name: str
    program_template: str
    mission_description: str
    data_files: dict[str, str] = field(default_factory=dict)
    # data_files 路径相对于 plugin_path
    evaluation_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "TaskConfig":
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)
        return from_dict(data_class=cls, data=config_dict, config=Config(strict=True, check_types=True))
