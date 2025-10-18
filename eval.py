import os
import argparse
import asyncio
import importlib
from dotenv import load_dotenv
from core.base import TaskPlugin
from core.base.config import TaskConfig
from evolution.config import CoreConfig
from evolution.main import EvolutionEngine


def main():
    # 加载环境变量
    load_dotenv()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行进化算法')
    parser.add_argument('--task-path', type=str, default='core/dictator_game',
                       help='任务路径 (默认: core/dictator_game)')
    parser.add_argument('--model', type=str, help='待评估的模型代码')
    
    args = parser.parse_args()
    
    # 动态导入插件类
    task_config = TaskConfig.from_yaml(os.path.join(args.task_path, "config.yaml"))
    print(f"初始化任务插件: {task_config.name}")
    module_path = f"core.{task_config.name}.plugin"
    module = importlib.import_module(module_path)
    PluginClass = getattr(module, task_config.plugin_name)
    task_plugin: TaskPlugin = PluginClass(task_config, args.task_path)

    # 显示配置信息
    print(f"\n配置信息:")
    print(f"  任务名称: {task_plugin.get_task_name()}")
    evaluator = task_plugin.create_evaluator()
    with open(args.model, "r") as f:
        model_code = f.read()
    
    result = evaluator.evaluate(model_code)
    import json
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    exit(main())
