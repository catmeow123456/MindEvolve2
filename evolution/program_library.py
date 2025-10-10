import os
import uuid
import json
import time
import random
from typing import Literal, Any, Optional, Tuple, Dict
from dataclasses import dataclass, field
from copy import deepcopy
from evolution.config import EvolutionSettingConfig

@dataclass
class Program:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    parent_ids: list[str] = field(default_factory=list)
    creation_method: Literal["mutation", "initial"] = "initial"
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_metrics(self, metrics: dict[str, float]) -> None:
        assert 'runs_successfully' in metrics
        self.metrics = metrics.copy()
        if 'combined_score' not in self.metrics:
            self.metrics['combined_score'] = Program.calc_combined_score(self.metrics)

    def update_metadata(self, metadata: dict[str, Any]) -> None:
        assert isinstance(metadata, dict)
        self.metadata = deepcopy(metadata)

    @staticmethod
    def calc_combined_score(metrics: dict[str, float]) -> float:
        if 'combined_score' in metrics:
            return metrics['combined_score']
        if float(metrics['runs_successfully']) == 0.0:
            return 0.0
        numeric_values = []
        for key, v in metrics.items():
            assert v >= 0 and v <= 1
            if key != 'runs_successfully':
                numeric_values.append(v)
        if len(numeric_values) == 0:
            raise ValueError(f"No numeric metrics found to calculate combined score in {metrics}")
        return sum(numeric_values) / len(numeric_values) * metrics['runs_successfully']

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "parent_ids": self.parent_ids,
            "creation_method": self.creation_method,
            "metrics": self.metrics,
            "metadata": self.metadata
        }



class ProgramLibrary:
    def __init__(self, save_dir: str):
        self.programs: dict[str, Program] = {}
        self.save_dir = save_dir
        if not self.save_dir:
            raise ValueError("请设置 save_dir 参数")
        os.makedirs(save_dir, exist_ok=True)
        
        # 如果存在历史存档，加载最新的
        json_files = [f for f in os.listdir(save_dir) if f.startswith('program_library_') and f.endswith('.json')]
        if json_files:
            latest_file = max(json_files)  # 按文件名排序，时间戳大的在后
            filepath = os.path.join(save_dir, latest_file)
            print(f"加载历史存档: {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for prog_id, prog_data in data['programs'].items():
                    program = Program(**prog_data)
                    self.programs[prog_id] = program
            print(f"已加载 {len(self.programs)} 个程序")

    def get_size(self) -> int:
        return len(self.programs)

    def _add_program(self, program: Program) -> str:
        self.programs[program.id] = program

    def add_program(
        self,
        content: str,
        metrics: Optional[Dict[str, float]],
        parent_ids: Optional[list[str]] = None,
        creation_method: Literal["mutation", "initial"] = "initial",        
        metadata: Optional[Dict[str, Any]] = None
    ) -> Program:
        program = Program(
            id = str(self.get_size() + 1),
            content = content,
            parent_ids = parent_ids or [],
            creation_method = creation_method,
        )
        program.update_metrics(metrics)
        if metadata:
            program.update_metadata(metadata)
        self._add_program(program)
        return program

    def save(self, filename: Optional[str] = None) -> str:
        if filename is None:
            timestamp = int(time.time())
            filename = f"program_library_{timestamp}.json"
        filepath = os.path.join(self.save_dir, filename)
        data = {
            "programs": {prog_id: prog.to_json() for prog_id, prog in self.programs.items()}
        }
        with open(filepath, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return filepath

    def sample_parent_inspiration_pairs(self, n: int) -> list[Tuple[Program, Program]]:
        """采样 n 对 parent program 和 inspiration program 元组用于之后的 mutation 生成后一代
        
        先用随机采样策略，以后可以更换成更合适的策略（如基于 fitness 的选择）
        """
        programs_list = list(self.programs.values())
        if len(programs_list) < 2:
            raise ValueError(f"至少需要 2 个程序才能采样，当前只有 {len(programs_list)} 个")
        
        pairs = []
        for _ in range(n):
            parent, inspiration = random.sample(programs_list, 2)
            pairs.append((parent, inspiration))
        return pairs
