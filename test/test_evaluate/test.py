from core.dictator_game.plugin import DictatorGamePlugin
from core.base.config import TaskConfig

task_config = TaskConfig.from_yaml("core/dictator_game/main/task_config.yaml")

game_plugin = DictatorGamePlugin(task_config, "core/dictator_game")

evaluator = game_plugin.create_evaluator()

res, metadata = evaluator.evaluate("""
# Sample model 1
import numpy as np

USER_PARAM_CONFIG = {
    "init_params": [0.5, 1.0],
    "bounds": [(0.0, 2.0), (0.0, 5.0)],
    "names": ["alpha", "beta"]
}

def probability_unfair(params, condition, unfair_self, unfair_other, fair_self, fair_other):
    alpha, beta = params
    utility_unfair = alpha * unfair_self + (1 - alpha) * unfair_other
    utility_fair = alpha * fair_self + (1 - alpha) * fair_other
    return 1 / (1 + np.exp(-beta * (utility_unfair - utility_fair)))
""")

print("Result:")
print(res)

print("Metadata:")
print(metadata)