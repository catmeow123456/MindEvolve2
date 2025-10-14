from core.base.plugin import TaskPlugin
from .evaluator import TrustGameEvaluator


class TrustGamePlugin(TaskPlugin):
    """Plugin for Trust Game Task"""

    def create_evaluator(self):
        evaluation_config = self.get_evaluation_config()
        data_files = self.get_data_files()
        return TrustGameEvaluator(evaluation_config, data_files)

    def get_mutation_prompt(self, parent: str, inspiration: str, parent_metadata: any = None, inspiration_metadata: any = None) -> str:
        """
        Generate mutation prompt using parent program with its reviewer comments and inspiration program
        
        Args:
            parent: Parent program code
            inspiration: Inspiration program code
            parent_metadata: Metadata containing reviewer comments for parent
            inspiration_metadata: Metadata containing reviewer comments for inspiration (not used)
            
        Returns:
            str: Mutation prompt for LLM
        """
        # Extract reviewer comments from parent metadata only
        parent_review_1 = "No theoretical review available."
        parent_review_2 = "No code quality review available."
        
        if parent_metadata:
            parent_review_1 = parent_metadata.get("reviewer_1_comment", "No theoretical review available.")
            parent_review_2 = parent_metadata.get("reviewer_2_comment", "No code quality review available.")
            if "error" in parent_metadata:
                parent_review_1 = f"ERROR: {parent_metadata.get('error')}"
                parent_review_2 = parent_review_1
        
        prompt = (
            "You are provided with a PARENT program (with detailed expert reviews) and an INSPIRATION program. "
            "The parent has been evaluated by two expert reviewers:\n"
            "- Reviewer 1 (Theoretical): Evaluates cognitive science and behavioral economics aspects\n"
            "- Reviewer 2 (Code Quality): Evaluates implementation quality and best practices\n\n"
            "Your task is to generate a NEW program that meaningfully improves upon the parent by addressing the identified weaknesses "
            "while incorporating successful mechanisms from the inspiration program.\n\n"
            "## CRITICAL REQUIREMENTS:\n"
            "1. The policy function MUST return exactly 5 probabilities: [p(invest 0), p(invest 5), p(invest 10), p(invest 15), p(invest 20)]\n"
            "2. The probabilities MUST sum to 1.0 (valid probability distribution)\n"
            "3. You MUST use the softmax formula with max subtraction: exp(utility - max(utilities)) to prevent overflow\n"
            "4. Handle edge cases (e.g., first round with no history)\n"
            "5. All required UserParameter fields must be used meaningfully in the model\n"
            "6. Implement proper Theory of Mind (recursive reasoning, not just historical averaging)\n"
            "7. Implement proper Planning (dynamic programming/Bellman equations, not just additive terms)\n\n"
            "## PARENT PROGRAM:\n"
            "```python\n"
            f"{parent}\n"
            "```\n\n"
            "## PARENT PROGRAM - THEORETICAL REVIEW (Reviewer 1):\n"
            f"{parent_review_1}\n\n"
            "## PARENT PROGRAM - CODE QUALITY REVIEW (Reviewer 2):\n"
            f"{parent_review_2}\n\n"
            "## INSPIRATION PROGRAM:\n"
            "```python\n"
            f"{inspiration}\n"
            "```\n\n"
            "## YOUR TASK:\n"
            "Based on the parent program's reviews:\n"
            "1. Identify the key weaknesses in the parent program (both theoretical and implementation) as highlighted by the reviewers\n"
            "2. Analyze the inspiration program to identify successful mechanisms or approaches\n"
            "3. Generate an improved program that:\n"
            "   - Addresses the theoretical weaknesses highlighted by Reviewer 1\n"
            "   - Fixes the code quality issues highlighted by Reviewer 2\n"
            "   - Incorporates successful mechanisms from the inspiration program\n"
            "   - Maintains or improves upon the parent's strengths\n\n"
            "Generate the improved program following this Python template:\n"
            "```python\n"
            f"{self.program_template}\n"
            "```\n\n"
            "Return ONLY the complete Python code with the policy function fully implemented. "
            "Do not include markdown code fences in your response, just the raw Python code."
        )
        
        return prompt
