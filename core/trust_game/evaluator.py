"""
Trust Game Evaluator - Main evaluator coordinating all components
"""
import os
from typing import Tuple, Dict, Any
from core.base import TaskEvaluator
from .utils import get_time, sha256_hash
from .reviewers import ModelReviewers
from .score_extractors import extract_scores_from_theoretical_review, extract_scores_from_code_review
from .model_tester import test_model_runs_successfully


class TrustGameEvaluator(TaskEvaluator):
    """
    Evaluator for Trust Game models
    Coordinates reviewers, score extraction, and model testing
    """
    
    def __init__(self, config: dict[str, any], data_files: dict[str, str]):
        super().__init__(config, data_files)
        self.game_data = data_files['game_data']
        
        # Load prompt templates
        prompt_review_1 = open(data_files['prompt_review_1'], 'r', encoding='utf-8').read()
        prompt_review_2 = open(data_files['prompt_review_2'], 'r', encoding='utf-8').read()
        prompt_standardize_theoretical = open(data_files['prompt_standardize_theoretical'], 'r', encoding='utf-8').read()
        prompt_standardize_code = open(data_files['prompt_standardize_code'], 'r', encoding='utf-8').read()
        
        # Initialize reviewers
        self.reviewers = ModelReviewers(config, prompt_review_1, prompt_review_2,
                                       prompt_standardize_theoretical, prompt_standardize_code)
        
        if not os.path.exists(self.game_data):
            raise ValueError(f"Data file {self.game_data} not found")

    def evaluate(self, model_code: str) -> Tuple[Dict[str, float], Any]:
        """
        Evaluate a trust game model using two LLM reviewers
        
        Args:
            model_code: The model code to evaluate
            
        Returns:
            Tuple[Dict[str, float], Any]: A tuple containing:
            - First element: Dict with metrics from both reviewers
            - Second element: Metadata containing full review comments
        """
        suffix = get_time() + "_" + sha256_hash(model_code)[:8]
        code_path = f"model_{suffix}.py"
        review_1_path = f"model_{suffix}_review1.md"
        review_2_path = f"model_{suffix}_review2.md"
        
        try:
            # Save model code for debugging
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(model_code)
            
            # Get reviews from both reviewers in parallel and standardize them
            print("开始并行评审模型...")
            review_1, review_2, standardized_1, standardized_2 = self.reviewers.review_and_standardize_parallel(model_code)
            print("评审完成")
            
            # Save original reviews for debugging
            with open(review_1_path, 'w', encoding='utf-8') as f:
                f.write(review_1)
            with open(review_2_path, 'w', encoding='utf-8') as f:
                f.write(review_2)
            
            # Save standardized reviews for debugging
            standardized_1_path = f"model_{suffix}_review1_standardized.md"
            standardized_2_path = f"model_{suffix}_review2_standardized.md"
            with open(standardized_1_path, 'w', encoding='utf-8') as f:
                f.write(standardized_1)
            with open(standardized_2_path, 'w', encoding='utf-8') as f:
                f.write(standardized_2)
            
            # Extract scores from standardized reviews
            reviewer_1_scores = extract_scores_from_theoretical_review(standardized_1)
            reviewer_2_scores = extract_scores_from_code_review(standardized_2)
            
            # Test model runs successfully (with parallel sample testing)
            print("测试模型是否能成功运行（并行测试）...")
            runs_successfully_score, runs_metadata = test_model_runs_successfully(
                model_code, 
                self.game_data,
                num_samples=5,
                num_rounds_per_sample=5,
                timeout_seconds=10.0,
                parallel=True  # Enable parallel testing
            )
            print(f"模型运行成功率: {runs_successfully_score:.2%}")
            
            # Combine metrics
            metrics = {
                "reviewer_1_overall": reviewer_1_scores.get("overall", 0.0),
                "reviewer_2_overall": reviewer_2_scores.get("overall", 0.0),
                "runs_successfully": runs_successfully_score,
            }
            
            # Store full comments in metadata
            metadata = {
                "reviewer_1_comment": review_1,
                "reviewer_2_comment": review_2,
                "reviewer_1_standardized": standardized_1,
                "reviewer_2_standardized": standardized_2,
                "reviewer_1_scores": reviewer_1_scores,
                "reviewer_2_scores": reviewer_2_scores,
                "runs_successfully_metadata": runs_metadata,
                "saved_files": {
                    "code": code_path,
                    "review_1": review_1_path,
                    "review_2": review_2_path,
                    "review_1_standardized": standardized_1_path,
                    "review_2_standardized": standardized_2_path
                }
            }
            
            print(f"已保存模型代码到: {code_path}")
            print(f"已保存理论评估到: {review_1_path}")
            print(f"已保存代码质量评估到: {review_2_path}")
            print(f"已保存标准化理论评估到: {standardized_1_path}")
            print(f"已保存标准化代码质量评估到: {standardized_2_path}")
            
            return metrics, metadata
            
        except Exception as e:
            print(f"评估失败: {e}")
            metadata = {"error": repr(e)}
            return {
                "reviewer_1_overall": 0.0,
                "reviewer_2_overall": 0.0,
                "combined_score": 0.0,
                "runs_successfully": 0.0,
            }, metadata

    def get_metric_names(self) -> list[str]:
        """Return list of metric names provided by this evaluator"""
        return ['reviewer_1_overall', 'reviewer_2_overall', 'combined_score', 'runs_successfully']
