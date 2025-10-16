#!/usr/bin/env python3
"""
独立的评估任务执行脚本
用于在远程节点上执行代码评估任务
"""
import argparse
import json
import sys
import traceback
from pathlib import Path
import dotenv

def main():
    parser = argparse.ArgumentParser(description='执行代码评估任务')
    parser.add_argument('--code-file', required=True, help='待评估的代码文件路径')
    parser.add_argument('--output-file', required=True, help='结果输出文件路径')
    args = parser.parse_args()
    
    code_file = Path(args.code_file)
    output_file = Path(args.output_file)
    
    result = {
        'success': False,
        'result': None,
        'metadata': None,
        'error': None
    }
    
    try:
        # 加载环境变量
        dotenv.load_dotenv()
        
        # 读取代码
        if not code_file.exists():
            raise FileNotFoundError(f"代码文件不存在: {code_file}")
        
        code = code_file.read_text(encoding='utf-8')
        
        # 导入必要的模块
        import core.task.plugin as plugin
        from core.base.config import TaskConfig
        
        # 加载任务配置
        task_config = TaskConfig.from_yaml("core/task/config.yaml")
        PluginClass = getattr(plugin, task_config.plugin_name)
        
        # 创建插件和评估器
        task_plugin = PluginClass(task_config, "core/task")
        evaluator = task_plugin.create_evaluator()
        
        # 执行评估
        eval_result, metadata = evaluator.evaluate(code)
        
        result['success'] = True
        result['result'] = eval_result
        result['metadata'] = metadata
        
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        print(f"评估失败: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    
    finally:
        # 写入结果
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"结果已写入: {output_file}")

if __name__ == '__main__':
    main()
