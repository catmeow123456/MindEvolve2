from abc import ABC, abstractmethod
from typing import Tuple
import os
import importlib.util


class TaskEvaluator(ABC):
    def __init__(self, config: dict[str, any], data_files: dict[str, str]):
        self.config = config
        self.data_files = data_files

    @abstractmethod
    def evaluate(self, model_code: str) -> Tuple[dict[str, float], any]:
        pass

    @abstractmethod
    def get_metric_names(self) -> list[str]:
        pass

def load_model_module(model_path: str):
    """
    Load {model_path} as a module
    """
    spec = importlib.util.spec_from_file_location("model", model_path)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    return model
