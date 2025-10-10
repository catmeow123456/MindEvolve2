import os
from typing import Tuple
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from pandas import DataFrame
from api import OpenAILLM, OpenAIConfig
from core.base import TaskEvaluator, load_model_module
import time
import datetime
import hashlib

class DictatorGameEvaluator(TaskEvaluator):
    def __init__(self, config: dict[str, any], data_files: dict[str, str]):
        super().__init__(config, data_files)
        self.behavioral_data = data_files['behavioral_data']
        self.prompt_review = open(data_files['prompt_review'], 'r', encoding='utf-8').read()
        self.review_llm_client = OpenAILLM(
            OpenAIConfig(**config["reviewer_llm"]),
            base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY")
        )
        if not os.path.exists(self.behavioral_data):
            raise ValueError(f"Data file {self.behavioral_data} not found")


    def evaluate(self, model_code: str) -> Tuple[dict[str, float], any]:
        """
        Evaluate a dictator game model
        
        Args:
            model_code: The model code to evaluate
            
        Returns:
            Tuple[Dict[str, float], Any]: A tuple containing:
            - First element: Dict with metrics including runs_successfully, bic_score
            - Second element: Meta data for the program evaluation information
        """
        suffix = self.get_time() + "_" + self.sha256_hash(model_code)[:8]
        code_path = f"model_{suffix}.py"
        result_path = f"result_{suffix}.csv"
        try:
            # Write model code to temporary file
            with open(code_path, 'w') as f:
                f.write(model_code)

            # Evaluate the model
            total_bic = self.evaluate_model(code_path, result_path)
            review = self.review_model(model_code)

            # Calculate standardized metrics
            mapped_bic_score = self.linear_map(total_bic, 4700, 6000, 1.0, 0.0)
            mapped_bic_score = max(0.0, min(1.0, mapped_bic_score))
            metrics = { "runs_successfully": 1.0, "bic_score": mapped_bic_score }
            metadata = { "bic": total_bic, "review": review }
            return metrics, metadata
            
        except Exception as e:
            print(f"评估失败: {e}")
            metadata = { "error": repr(e) }
            return { "runs_successfully": 0.0, "bic_score": 0.0 }, metadata

    def get_metric_names(self) -> list[str]:
        return ['runs_successfully', 'bic_score']


    def review_model(self, model_code: str) -> str:
        content = self.prompt_review
        if "{model}" not in content:
            raise ValueError("Prompt review must contain {model} placeholder")
        content = content.replace("{model}", model_code)
        review = self.review_llm_client.generate(content)
        return review

    def evaluate_model(self, model_path: str, result_path: str = "temp.csv") -> float:
        """
        Evaluate a single model file
        
        Args:
            model_path: Path to model.py
            result_path: Path to save fitted results CSV
            
        Returns:
            Dict with evaluation results
        """
        # Load model module
        model = load_model_module(model_path)
        USER_PARAM_CONFIG = model.USER_PARAM_CONFIG
        probability_unfair = model.probability_unfair

        # Read data
        df = pd.read_csv(self.behavioral_data)

        # Model parameter configuration - handle different formats
        # Try the expected format first
        if "init_params" in USER_PARAM_CONFIG:
            init_params = USER_PARAM_CONFIG["init_params"]
            bounds = USER_PARAM_CONFIG["bounds"]
            param_names = USER_PARAM_CONFIG["names"]
        # Handle LLM generated format
        elif "default_values" in USER_PARAM_CONFIG:
            init_params = USER_PARAM_CONFIG["default_values"]
            bounds = USER_PARAM_CONFIG["param_bounds"]
            param_names = USER_PARAM_CONFIG["param_names"]
        else:
            # Try to infer from available keys
            possible_init_keys = ["init_params", "default_values", "initial_values"]
            possible_bounds_keys = ["bounds", "param_bounds", "parameter_bounds"]
            possible_names_keys = ["names", "param_names", "parameter_names"]
            
            init_params = None
            bounds = None
            param_names = None
            
            for key in possible_init_keys:
                if key in USER_PARAM_CONFIG:
                    init_params = USER_PARAM_CONFIG[key]
                    break
            
            for key in possible_bounds_keys:
                if key in USER_PARAM_CONFIG:
                    bounds = USER_PARAM_CONFIG[key]
                    break
            
            for key in possible_names_keys:
                if key in USER_PARAM_CONFIG:
                    param_names = USER_PARAM_CONFIG[key]
                    break
            
            if init_params is None or bounds is None or param_names is None:
                raise KeyError(f"无法找到必需的参数配置。可用键: {list(USER_PARAM_CONFIG.keys())}")
        
        k = len(init_params)

        # Fit for each participant
        results = []
        for subject_id in df["subject"].unique():
            sub_df = df[df["subject"] == subject_id]

            res = minimize(
                self.neg_log_likelihood,
                init_params,
                args=(sub_df, probability_unfair),
                method="L-BFGS-B",
                bounds=bounds,
            )

            if not res.success:
                warnings.warn(f"Optimization failed for subject {subject_id}: {res.message}")

            fitted_params = res.x
            nll = self.neg_log_likelihood(res.x, sub_df, probability_unfair)
            result = {param_names[i]: fitted_params[i] for i in range(k)}
            result["subject"] = subject_id
            result["nll"] = nll
            results.append(result)

        # Save results
        results_df = pd.DataFrame(results)
        results_df.to_csv(result_path, index=False)
        print(f"模型拟合完成，结果已保存到 {result_path}")

        total_nll = results_df["nll"].sum()
        total_bic = 2 * total_nll + k * np.log(7200)
        print(f"Total BIC across all participants: {total_bic:.2f}")
        
        return float(total_bic)

    def neg_log_likelihood(self, params: list[float], sub_df: DataFrame, probability_unfair):
        """Calculate negative log likelihood"""
        log_likelihood = 0

        for _, row in sub_df.iterrows():
            cond = int(row["condition"]) - 1  # 0~3
            unfair_self = row["self_value"]
            unfair_other = row["other_value"]
            fair_self = 10
            fair_other = 10

            prob_unfair = probability_unfair(
                params, cond,
                unfair_self, unfair_other, fair_self, fair_other
            )
            prob_unfair = np.clip(prob_unfair, 1e-10, 1 - 1e-10)  # Avoid log(0)

            # Actual choice
            choice = row["choice"]  # 1: choose unfair option, 2: choose fair option

            if choice == 1:
                log_likelihood += np.log(prob_unfair)
            else:
                log_likelihood += np.log(1 - prob_unfair)

        return -log_likelihood  # Minimize negative log likelihood
    
    def linear_map(self, value: float, input_min: float, input_max: float, 
                   output_min: float, output_max: float) -> float:
        """Linear mapping function"""
        return (value - input_min) * (output_max - output_min) / (input_max - input_min) + output_min
    
    def get_time(self) -> str:
        """Get current timestamp"""
        return datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H:%M:%S.%f")
    
    def sha256_hash(self, text: str) -> str:
        """Calculate SHA256 hash"""
        sha256 = hashlib.sha256()
        sha256.update(text.encode('utf-8'))
        return sha256.hexdigest()
