from core.base.plugin import TaskPlugin
from .evaluator import DictatorGameEvaluator

class DictatorGamePlugin(TaskPlugin):
    """Plugin for Dictator Game Task"""

    def create_evaluator(self):
        evaluation_config = self.get_evaluation_config()
        data_files = self.get_data_files()
        return DictatorGameEvaluator(evaluation_config, data_files)

    def get_mutation_prompt(self, parent: str, inspiration: str, parent_metadata: any = None, inspiration_metadata: any = None) -> str:
        parent_review = parent_metadata.get("review", parent_metadata.get("error"))
        inspiration_review = inspiration_metadata.get("review", inspiration_metadata.get("error"))
        prompt = (
            "You are provided with a PARENT program, an INSPIRATION program, and their respective reviews. "
            "Generate a new python program that meaningfully improves upon the parent while considering the insights from both reviews. "
            "CRITICAL REQUIREMENTS:\n"
            "1. Keep all required function signatures EXACTLY unchanged\n"
            "2. USER_PARAM_CONFIG must contain exactly these keys: 'init_params', 'bounds', 'names'\n"
            "3. The probability_unfair function MUST have exactly this signature:\n"
            "   def probability_unfair(params, cond, unfair_self, unfair_other, fair_self=10, fair_other=10)\n"
            "4. Return ONLY the complete Python code without markdown fences\n"
            "5. Ensure the function actually implements the logic, not just placeholder comments\n\n"
            "PARENT PROGRAM:\n"
            f"{parent}\n\n"
            "PARENT REVIEW:\n"
            f"{parent_review}\n\n"
            "INSPIRATION PROGRAM:\n"
            f"{inspiration}\n\n"
            "INSPIRATION REVIEW:\n"
            f"{inspiration_review}\n\n"
            "Generate the improved program following the requirements above:"
        )
        return prompt
