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
        if 'runs_successfully' not in metrics:
            raise ValueError(f"Metrics {metrics} do not have `runs_successfully` key")
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

    def sample_parent_inspiration_pairs(self, n: int, program_pool_size: int = 10) -> list[Tuple[Program, Program]]:
        """采样 n 对 parent program 和 inspiration program 元组用于之后的 mutation 生成后一代
        
        使用非支配排序配对策略：
        1. 按 combined_score 排序，取前 program_pool_size 名
        2. 对这个池子进行非支配排序，分成多个前沿（F1, F2, ...）
        3. 配对策略：
           - 同一前沿内随机配对
           - 不同前沿间的精英与非精英配对
        """
        programs_list = list(self.programs.values())
        if len(programs_list) < 2:
            raise ValueError(f"至少需要 2 个程序才能采样，当前只有 {len(programs_list)} 个")
        
        # 1. 按 combined_score 排序取前 program_pool_size 名
        sorted_programs = sorted(
            programs_list, 
            key=lambda p: p.metrics.get('combined_score', 0.0), 
            reverse=True
        )
        pool = sorted_programs[:min(program_pool_size, len(sorted_programs))]
        
        # 2. 提取多维度指标（排除 runs_successfully 和 combined_score）
        def get_objectives(prog: Program) -> list[float]:
            """提取用于 Pareto 比较的多维度指标"""
            return [v for k, v in prog.metrics.items() 
                    if k not in ('runs_successfully', 'combined_score')]
        
        # 3. 判断 Pareto 支配关系
        def dominates(prog_a: Program, prog_b: Program) -> bool:
            """判断 prog_a 是否 Pareto 支配 prog_b"""
            objs_a = get_objectives(prog_a)
            objs_b = get_objectives(prog_b)
            if not objs_a:  # 没有其他维度指标
                return False
            # a 支配 b：在所有维度上不劣于 b，且至少在一个维度上优于 b
            better_or_equal = all(a >= b for a, b in zip(objs_a, objs_b))
            strictly_better = any(a > b for a, b in zip(objs_a, objs_b))
            return better_or_equal and strictly_better
        
        # 4. 非支配排序：将程序分成多个前沿
        fronts = []  # 前沿列表，每个前沿是一个程序列表
        remaining = pool.copy()
        
        while remaining:
            current_front = []
            for prog in remaining:
                # 检查是否被 remaining 中的其他程序支配
                is_dominated = any(dominates(other, prog) for other in remaining if other.id != prog.id)
                if not is_dominated:
                    current_front.append(prog)
            
            if current_front:
                fronts.append(current_front)
                # 从 remaining 中移除当前前沿的程序
                remaining = [p for p in remaining if p not in current_front]
            else:
                # 防止死循环：如果没有非支配解，将剩余所有程序作为一个前沿
                fronts.append(remaining)
                break
        
        # 5. 边界情况处理：如果只有一个前沿且程序数少于2，回退到全部池子
        if len(fronts) == 1 and len(fronts[0]) < 2:
            fronts = [pool[:min(10, len(pool))]]
        
        # 6. 配对策略
        pairs = []
        for _ in range(n):
            # 随机选择配对策略：50% 同一前沿内配对，50% 不同前沿间配对
            if len(fronts) == 1 or random.random() < 0.5:
                # 同一前沿内配对：随机选择一个前沿
                front = random.choice(fronts)
                if len(front) >= 2:
                    parent, inspiration = random.sample(front, 2)
                else:
                    # 如果前沿只有1个程序，从所有程序中采样
                    all_progs = [p for f in fronts for p in f]
                    parent, inspiration = random.sample(all_progs, 2)
            else:
                # 不同前沿间配对：精英前沿（索引小）与非精英前沿（索引大）
                elite_fronts = fronts[:len(fronts)//2] if len(fronts) > 1 else [fronts[0]]
                non_elite_fronts = fronts[len(fronts)//2:] if len(fronts) > 1 else [fronts[0]]
                
                parent = random.choice([p for f in elite_fronts for p in f])
                inspiration = random.choice([p for f in non_elite_fronts for p in f])
            
            pairs.append((parent, inspiration))
        
        return pairs
