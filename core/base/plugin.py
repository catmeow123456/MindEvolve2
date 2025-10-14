"""
Base plugin class for task-specific implementations
"""
import os
from abc import ABC, abstractmethod
from core.base.config import TaskConfig
from core.base.evaluator import TaskEvaluator
from copy import deepcopy


class TaskPlugin(ABC):
    """Abstract base class for task plugins"""
    task_path: str
    config: TaskConfig
    program_template: str
    mission_description: str

    def __init__(self, task_config: TaskConfig, task_path: str):
        self.task_path = task_path
        self.config = task_config
        for name in self.config.data_files:
            data_file_path = os.path.join(task_path, "main", self.config.data_files[name])
            if not os.path.exists(data_file_path):
                raise ValueError(f"File `{self.config.data_files[name]}` not found in directory {task_path}")
            self.config.data_files[name] = data_file_path
            
        program_template_path = os.path.join(task_path, "main", self.config.program_template)
        if not os.path.exists(program_template_path):
            raise ValueError(f"Program template not found: {self.config.program_template}")
        self.program_template = open(program_template_path, 'r', encoding='utf-8').read()
        self.mission_description = self.config.mission_description

    def get_program_template(self) -> str:
        return self.program_template

    def get_mission_description(self) -> str:
        return self.mission_description

    def get_task_name(self) -> str:
        """Return task name"""
        return self.config.name
    
    def get_data_files(self) -> dict[str, str]:
        """Return data files mapping"""
        return self.config.data_files.copy()
    
    def get_evaluation_config(self) -> dict[str, any]:
        """Return evaluation configuration"""
        return deepcopy(self.config.evaluation_config)

    def get_initial_prompt(self) -> str:
        """Return initial prompt for LLM"""
        initial_prompt = (
            f"{self.mission_description}\n"
            "You must complete the following Python template to create a program that solves the task.\n"
            "TEMPLATE TO COMPLETE:\n"
            "```python\n"
            f"{self.program_template}\n"
            "```\n"
            "Return ONLY the Python code:"
        )
        return initial_prompt

    def get_mutation_prompt(self, parent: str, inspiration: str, parent_metadata: any = None, inspiration_metadata: any = None) -> str:
        """Return mutation prompt for LLM"""
        mutation_prompt = (
            "You are provided with a PARENT program, an INSPIRATION program."
            "Generate a new python program that meaningfully improves upon the parent while considering the inspiration program. "
            "PARENT PROGRAM:\n"
            "```python\n"
            f"{parent}\n"
            "```\n"
            "INSPIRATION PROGRAM:\n"
            "```python\n"
            f"{inspiration}\n"
            "```\n"
            "Generate an improved program according to the following Python template:\n"
            "```python\n"
            f"{self.program_template}\n"
            "```\n"
            "Return ONLY the Python code:"
        )
        return mutation_prompt

    @abstractmethod
    def create_evaluator(self) -> TaskEvaluator:
        """Return task-specific evaluator"""
        pass
