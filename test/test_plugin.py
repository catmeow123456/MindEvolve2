from core.dictator_game.plugin import DictatorGamePlugin
from core.base.config import TaskConfig

task_config = TaskConfig.from_yaml("core/dictator_game/config.yaml")

game_plugin = DictatorGamePlugin(task_config, "core/dictator_game")

print("Task Name:")
print(game_plugin.get_task_name())
print()

print("Data Files:")
print(game_plugin.get_data_files())
print()

print("Evaluation Config:")
print(game_plugin.get_evaluation_config())
print()

print("Initial Prompt:")
print(game_plugin.get_initial_prompt()[:50], "...")
print()

print("Mission Description")
print(game_plugin.get_mission_description()[:50], "...")
print()

print("Program Template:")
print(game_plugin.get_program_template()[:50], "...")
print()
