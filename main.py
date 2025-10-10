import os
import argparse
from dotenv import load_dotenv
from core.base.config import TaskConfig
from core.dictator_game.plugin import DictatorGamePlugin
from evolution.config import CoreConfig
from evolution.main import EvolutionEngine


def main():
    # 加载环境变量
    load_dotenv()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行进化算法')
    parser.add_argument('--config', type=str, default='evolution/test/config_test.yaml',
                       help='进化算法配置文件路径 (默认: evolution/test/config_test.yaml)')
    parser.add_argument('--task-config', type=str, default='core/dictator_game/config.yaml',
                       help='任务配置文件路径 (默认: core/dictator_game/config.yaml)')
    parser.add_argument('--task-path', type=str, default='core/dictator_game',
                       help='任务路径 (默认: core/dictator_game)')
    parser.add_argument('--output-dir', type=str, default='output/dictator_game',
                       help='输出目录 (默认: output/dictator_game')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MindEvolve v2 - 进化算法启动")
    print("=" * 60)
    
    # 加载配置
    print(f"\n加载进化算法配置: {args.config}")
    core_config = CoreConfig.from_yaml(args.config)
    
    print(f"加载任务配置: {args.task_config}")
    task_config = TaskConfig.from_yaml(args.task_config)
    
    # 创建任务插件
    print(f"初始化任务插件: {task_config.name}")
    task_plugin = DictatorGamePlugin(task_config, args.task_path)
    
    # 创建进化引擎
    print("初始化进化引擎...")
    engine = EvolutionEngine(task_plugin, core_config)
    
    # 显示配置信息
    print(f"\n配置信息:")
    print(f"  任务名称: {task_plugin.get_task_name()}")
    print(f"  LLM 模型: {core_config.llm.model}")
    print(f"  最大迭代数: {core_config.evolution_setting.max_iterations}")
    print(f"  种群大小: {core_config.evolution_setting.program_pool_size}")
    print(f"  输出目录: {os.path.abspath(args.output_dir)}")
    
    # 运行进化算法
    print(f"\n{'=' * 60}")
    print("开始进化算法...")
    print(f"{'=' * 60}\n")
    
    try:
        library = engine.run_evolution(
            task_dir=args.task_path,
            save_dir=args.output_dir
        )
        
        print(f"\n{'=' * 60}")
        print("进化算法完成!")
        print(f"{'=' * 60}")
        print(f"总计生成程序数: {library.get_size()}")
        
        # 显示最佳程序
        if library.get_size() > 0:
            best_program = max(
                library.programs.values(),
                key=lambda p: p.metrics.get('combined_score', 0)
            )
            print(f"\n最佳程序:")
            print(f"  ID: {best_program.id}")
            print(f"  Combined Score: {best_program.metrics.get('combined_score', 0):.4f}")
            print(f"  创建方法: {best_program.creation_method}")
            if best_program.parent_ids:
                print(f"  父代 ID: {best_program.parent_ids}")
        
    except KeyboardInterrupt:
        print("\n\n检测到中断信号，正在退出...")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
