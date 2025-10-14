import os
import re
import csv
import tempfile
import sys
import multiprocessing
from typing import Tuple, Dict, Any, List
from api import AnthropicLLM, AnthropicConfig
from core.base import TaskEvaluator
import time
import datetime
import hashlib
import random


class TrustGameEvaluator(TaskEvaluator):
    def __init__(self, config: dict[str, any], data_files: dict[str, str]):
        super().__init__(config, data_files)
        self.game_data = data_files['game_data']
        self.prompt_review_1 = open(data_files['prompt_review_1'], 'r', encoding='utf-8').read()
        self.prompt_review_2 = open(data_files['prompt_review_2'], 'r', encoding='utf-8').read()
        
        # Create LLM client for reviewers with thinking enabled
        self.review_llm_client = AnthropicLLM(
            AnthropicConfig(**config["reviewer_llm"]),
            base_url=os.getenv("ANTHROPIC_BASE_URL"), 
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
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
        suffix = self.get_time() + "_" + self.sha256_hash(model_code)[:8]
        code_path = f"model_{suffix}.py"
        review_1_path = f"model_{suffix}_review1.md"
        review_2_path = f"model_{suffix}_review2.md"
        
        try:
            # Save model code for debugging
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(model_code)
            
            # Get reviews from both reviewers
            review_1 = self.review_model_theoretical(model_code)
            review_2 = self.review_model_code_quality(model_code)
            
            # Save reviews for debugging
            with open(review_1_path, 'w', encoding='utf-8') as f:
                f.write(review_1)
            with open(review_2_path, 'w', encoding='utf-8') as f:
                f.write(review_2)
            
            # Extract scores from reviews
            reviewer_1_scores = self.extract_scores_from_theoretical_review(review_1)
            reviewer_2_scores = self.extract_scores_from_code_review(review_2)
            
            # Test model runs successfully
            print("测试模型是否能成功运行...")
            runs_successfully_score, runs_metadata = self.test_model_runs_successfully(model_code)
            print(f"模型运行成功率: {runs_successfully_score:.2%}")
            
            # Combine metrics
            metrics = {
                "reviewer_1_overall": reviewer_1_scores.get("overall", 0.0),
                "reviewer_2_overall": reviewer_2_scores.get("overall", 0.0),
                "combined_score": (reviewer_1_scores.get("overall", 0.0) + reviewer_2_scores.get("overall", 0.0)) / 2.0,
                "runs_successfully": runs_successfully_score
            }
            
            # Store full comments in metadata
            metadata = {
                "reviewer_1_comment": review_1,
                "reviewer_2_comment": review_2,
                "reviewer_1_scores": reviewer_1_scores,
                "reviewer_2_scores": reviewer_2_scores,
                "runs_successfully_metadata": runs_metadata,
                "saved_files": {
                    "code": code_path,
                    "review_1": review_1_path,
                    "review_2": review_2_path
                }
            }
            
            print(f"已保存模型代码到: {code_path}")
            print(f"已保存理论评估到: {review_1_path}")
            print(f"已保存代码质量评估到: {review_2_path}")
            
            return metrics, metadata
            
        except Exception as e:
            print(f"评估失败: {e}")
            metadata = {"error": repr(e)}
            return {
                "reviewer_1_overall": 0.0,
                "reviewer_2_overall": 0.0,
                "combined_score": 0.0,
                "runs_successfully": 0.0
            }, metadata

    def get_metric_names(self) -> list[str]:
        return ['reviewer_1_overall', 'reviewer_2_overall', 'combined_score', 'runs_successfully']

    def review_model_theoretical(self, model_code: str) -> str:
        """Get theoretical review from reviewer 1"""
        content = self.prompt_review_1
        if "{model}" not in content:
            raise ValueError("Prompt review 1 must contain {model} placeholder")
        content = content.replace("{model}", model_code)
        review = self.review_llm_client.generate(content)
        return review

    def review_model_code_quality(self, model_code: str) -> str:
        """Get code quality review from reviewer 2"""
        content = self.prompt_review_2
        if "{model}" not in content:
            raise ValueError("Prompt review 2 must contain {model} placeholder")
        content = content.replace("{model}", model_code)
        review = self.review_llm_client.generate(content)
        return review

    def extract_scores_from_theoretical_review(self, review: str) -> Dict[str, float]:
        """
        Extract scores from theoretical review (Reviewer 1)
        Looks for dimension scores and Overall Interpretability Score
        Uses multiple robust parsing strategies with fallbacks
        """
        scores = {}
        
        # Strategy 1: Try to extract the Overall Interpretability Score with multiple patterns
        interpretability_patterns = [
            r"Overall Interpretability Score:\s*\[(\d+)\]",  # Most specific
            r"Overall Interpretability Score:\s*(\d+)",      # Without brackets
            r"Interpretability Score:\s*\[(\d+)\]",
            r"Interpretability Score:\s*(\d+)",
            r"6\.\s*Overall.*?Score:\s*\[(\d+)\]",          # With numbering
            r"6\.\s*Overall.*?Score:\s*(\d+)",
        ]
        
        for pattern in interpretability_patterns:
            match = re.search(pattern, review, re.IGNORECASE)
            if match:
                score_value = float(match.group(1))
                if 0 <= score_value <= 100:  # Validate range
                    scores["interpretability"] = score_value / 100.0
                    scores["overall"] = score_value / 100.0
                    break
        
        # Strategy 2: Extract dimension scores (Yes=1.0, Partially=0.5, No=0.0)
        dimensions = [
            ("Payoff Calculation", "payoff"),
            ("Subjective Utility - Economic Preference", "economic"),
            ("Subjective Utility - Social Preference", "social"),
            ("Theory of Mind", "tom"),
            ("Planning", "planning")
        ]
        
        dimension_scores = []
        for dim_name, dim_key in dimensions:
            # Try multiple patterns for each dimension
            patterns = [
                rf"{re.escape(dim_name)}:\s*\[(Yes|Partially|No)\]",
                rf"{re.escape(dim_name)}:\s*(Yes|Partially|No)",
                rf"\d+\.\s*\*?\*?{re.escape(dim_name)}\*?\*?:\s*\[(Yes|Partially|No)\]",
                rf"\d+\.\s*\*?\*?{re.escape(dim_name)}\*?\*?:\s*(Yes|Partially|No)",
            ]
            
            found = False
            for pattern in patterns:
                match = re.search(pattern, review, re.IGNORECASE)
                if match:
                    response = match.group(1).lower()
                    if response == "yes":
                        score = 1.0
                    elif response == "partially":
                        score = 0.5
                    else:  # no
                        score = 0.0
                    
                    dimension_scores.append(score)
                    scores[dim_key] = score
                    found = True
                    break
            
            if not found:
                # Additional fallback: look for "Yes", "No", "Partially" near the dimension name
                context_pattern = rf"{re.escape(dim_name)}[^\n]{{0,100}}(Yes|Partially|No)"
                match = re.search(context_pattern, review, re.IGNORECASE)
                if match:
                    response = match.group(1).lower()
                    score = 1.0 if response == "yes" else (0.5 if response == "partially" else 0.0)
                    dimension_scores.append(score)
                    scores[dim_key] = score
        
        # Calculate dimension average if we got any scores
        if dimension_scores:
            scores["dimension_average"] = sum(dimension_scores) / len(dimension_scores)
        
        # Final fallback: if no overall score was found, use dimension average or default
        if "overall" not in scores:
            if "dimension_average" in scores:
                scores["overall"] = scores["dimension_average"]
            else:
                # Last resort: try to find any number that looks like a score
                all_scores = re.findall(r'\b(\d{1,3})\b', review)
                valid_scores = [float(s) / 100.0 for s in all_scores if 0 <= int(s) <= 100]
                if valid_scores:
                    scores["overall"] = sum(valid_scores) / len(valid_scores)
                else:
                    scores["overall"] = 0.5  # Default fallback
        
        return scores

    def extract_scores_from_code_review(self, review: str) -> Dict[str, float]:
        """
        Extract scores from code quality review (Reviewer 2)
        Looks for dimension scores (0-100) and Overall Code Quality Score
        Uses multiple robust parsing strategies with fallbacks
        """
        scores = {}
        
        # Strategy 1: Try to extract the Overall Code Quality Score with multiple patterns
        overall_patterns = [
            r"Overall Code Quality Score:\s*\[(\d+)\]",  # Most specific with brackets
            r"Overall Code Quality Score:\s*(\d+)",      # Without brackets
            r"Overall.*?Quality.*?Score:\s*\[(\d+)\]",
            r"Overall.*?Quality.*?Score:\s*(\d+)",
            r"Overall Score:\s*\[(\d+)\]",
            r"Overall Score:\s*(\d+)",
        ]
        
        for pattern in overall_patterns:
            match = re.search(pattern, review, re.IGNORECASE)
            if match:
                score_value = float(match.group(1))
                if 0 <= score_value <= 100:  # Validate range
                    scores["overall"] = score_value / 100.0
                    break
        
        # Strategy 2: Extract dimension scores with multiple patterns
        dimensions = [
            ("Code Clarity and Readability", "clarity"),
            ("Correctness and Robustness", "correctness"),
            ("Computational Efficiency", "efficiency"),
            ("Code Organization and Modularity", "organization"),
            ("Best Practices Compliance", "practices"),
            ("Documentation Quality", "documentation")
        ]
        
        dimension_scores = []
        for dim_name, dim_key in dimensions:
            # Try multiple patterns for each dimension
            patterns = [
                rf"{re.escape(dim_name)}:\s*\[(\d+)\]",  # With brackets
                rf"{re.escape(dim_name)}:\s*(\d+)",       # Without brackets
                rf"\d+\.\s*\*?\*?{re.escape(dim_name)}\*?\*?:\s*\[(\d+)\]",
                rf"\d+\.\s*\*?\*?{re.escape(dim_name)}\*?\*?:\s*(\d+)",
            ]
            
            found = False
            for pattern in patterns:
                match = re.search(pattern, review, re.IGNORECASE)
                if match:
                    score_value = float(match.group(1))
                    if 0 <= score_value <= 100:  # Validate range
                        score = score_value / 100.0
                        dimension_scores.append(score)
                        scores[dim_key] = score
                        found = True
                        break
            
            if not found:
                # Additional fallback: look for score near the dimension name
                # Match patterns like "Code Clarity... [85]" or "1. Code Clarity: 85"
                context_pattern = rf"{re.escape(dim_name)}[^\n]{{0,50}}\[?(\d{{1,3}})\]?"
                match = re.search(context_pattern, review, re.IGNORECASE)
                if match:
                    score_value = float(match.group(1))
                    if 0 <= score_value <= 100:
                        score = score_value / 100.0
                        dimension_scores.append(score)
                        scores[dim_key] = score
        
        # Calculate dimension average if we got any scores
        if dimension_scores:
            scores["dimension_average"] = sum(dimension_scores) / len(dimension_scores)
        
        # Final fallback: if no overall score was found, use dimension average or default
        if "overall" not in scores:
            if "dimension_average" in scores:
                scores["overall"] = scores["dimension_average"]
            else:
                # Last resort: try to find any reasonable score in the review
                # Look for patterns like "Score: 85" or "[85]"
                score_patterns = [
                    r"(?:Score|Rating|Grade):\s*\[?(\d{1,3})\]?",
                    r"\[(\d{1,3})\]",
                ]
                all_found_scores = []
                for pattern in score_patterns:
                    matches = re.findall(pattern, review, re.IGNORECASE)
                    for match in matches:
                        score_value = int(match)
                        if 0 <= score_value <= 100:
                            all_found_scores.append(score_value / 100.0)
                
                if all_found_scores:
                    scores["overall"] = sum(all_found_scores) / len(all_found_scores)
                else:
                    scores["overall"] = 0.5  # Default fallback
        
        return scores

    def get_time(self) -> str:
        """Get current timestamp"""
        return datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H:%M:%S.%f")
    
    def sha256_hash(self, text: str) -> str:
        """Calculate SHA256 hash"""
        sha256 = hashlib.sha256()
        sha256.update(text.encode('utf-8'))
        return sha256.hexdigest()

    def _run_policy_with_timeout(self, model_code: str, state_dict: dict, user_param_dict: dict, 
                                  timeout: float, result_queue: multiprocessing.Queue):
        """
        Helper function to run policy in a separate process with timeout
        This runs in a child process
        """
        try:
            # Create a temporary module to execute the code
            namespace = {}
            exec(model_code, namespace)
            
            # Check if policy function exists
            if 'policy' not in namespace:
                result_queue.put({"success": False, "error": "policy function not found"})
                return
            
            # Reconstruct State and UserParameter from dicts
            # First, reconstruct the State class if it exists in namespace
            if 'State' in namespace:
                StateClass = namespace['State']
            else:
                # Define State class if not in model code
                class StateClass:
                    def __init__(self, round: int, history: List[Tuple[int, int]]):
                        self.round = round
                        self.history = history
            
            # Reconstruct UserParameter if needed
            if 'UserParameter' in namespace:
                UserParamClass = namespace['UserParameter']
            else:
                # Define UserParameter class if not in model code
                class UserParamClass:
                    def __init__(self, inequalityAversion: float, riskAversion: float,
                                theoryOfMindSophistication: int, planning: float,
                                irritability: float, irritationAwareness: int,
                                inverseTemperature: float):
                        self.inequalityAversion = inequalityAversion
                        self.riskAversion = riskAversion
                        self.theoryOfMindSophistication = theoryOfMindSophistication
                        self.planning = planning
                        self.irritability = irritability
                        self.irritationAwareness = irritationAwareness
                        self.inverseTemperature = inverseTemperature
            
            # Create state object
            state = StateClass(
                round=state_dict['round'],
                history=[(int(x), int(y)) for x, y in state_dict['history']]
            )
            
            # Create user parameter object
            user_param = UserParamClass(**user_param_dict)
            
            # Call policy function
            policy_func = namespace['policy']
            result = policy_func(user_param, state)
            
            # Validate result
            if not isinstance(result, (list, tuple)):
                result_queue.put({"success": False, "error": f"policy returned {type(result)}, expected list"})
                return
            
            if len(result) != 5:
                result_queue.put({"success": False, "error": f"policy returned list of length {len(result)}, expected 5"})
                return
            
            # Check if all values are numeric and non-negative
            try:
                probs = [float(x) for x in result]
                if any(p < 0 for p in probs):
                    result_queue.put({"success": False, "error": "policy returned negative probabilities"})
                    return
                
                # Check if sum is close to 1.0 (allow small numerical error)
                total = sum(probs)
                if abs(total - 1.0) > 0.01:
                    result_queue.put({"success": False, "error": f"policy probabilities sum to {total}, expected ~1.0"})
                    return
                    
            except (ValueError, TypeError) as e:
                result_queue.put({"success": False, "error": f"policy returned non-numeric values: {e}"})
                return
            
            result_queue.put({"success": True, "result": probs})
            
        except Exception as e:
            result_queue.put({"success": False, "error": str(e)})

    def test_model_runs_successfully(self, model_code: str, num_samples: int = 5, 
                                      num_rounds_per_sample: int = 5, 
                                      timeout_seconds: float = 10.0) -> Tuple[float, Dict[str, Any]]:
        """
        Test if the model runs successfully on sample data
        
        Args:
            model_code: The model code to test
            num_samples: Number of data rows to sample
            num_rounds_per_sample: Number of rounds to test per sample (max 10)
            timeout_seconds: Timeout for each policy call
            
        Returns:
            Tuple[float, Dict]: Success rate (0.0-1.0) and metadata with details
        """
        try:
            # Read CSV data
            with open(self.game_data, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                data_rows = list(reader)
            
            if len(data_rows) == 0:
                return 0.0, {"error": "No data in CSV file"}
            
            # Sample rows
            sampled_rows = random.sample(data_rows, min(num_samples, len(data_rows)))
            
            # Default user parameters (can be randomized if needed)
            default_user_params = {
                'inequalityAversion': 0.4,
                'riskAversion': 1.0,
                'theoryOfMindSophistication': 2,
                'planning': 2.0,
                'irritability': 0.5,
                'irritationAwareness': 2,
                'inverseTemperature': 0.5
            }
            
            total_tests = 0
            successful_tests = 0
            test_details = []
            
            for row_idx, row in enumerate(sampled_rows):
                # Extract investor and trustee data
                investor_actions = []
                trustee_actions = []
                
                for i in range(1, 11):  # X1-X10 for investor, X11-X20 for trustee
                    try:
                        investor_actions.append(int(row[f'X{i}'].strip().strip('"')))
                        trustee_actions.append(int(row[f'X{i+10}'].strip().strip('"')))
                    except (ValueError, KeyError) as e:
                        test_details.append({
                            'row': row_idx,
                            'round': i-1,
                            'success': False,
                            'error': f'Failed to parse data: {e}'
                        })
                        continue
                
                # Test multiple rounds for this sample
                num_rounds = min(num_rounds_per_sample, len(investor_actions))
                
                for round_num in range(num_rounds):
                    total_tests += 1
                    
                    # Construct history up to this round
                    history = []
                    for j in range(round_num):
                        history.append((investor_actions[j], trustee_actions[j]))
                    
                    state_dict = {
                        'round': round_num,
                        'history': history
                    }
                    
                    # Create a queue for inter-process communication
                    result_queue = multiprocessing.Queue()
                    
                    # Run in separate process with timeout
                    process = multiprocessing.Process(
                        target=self._run_policy_with_timeout,
                        args=(model_code, state_dict, default_user_params, timeout_seconds, result_queue)
                    )
                    
                    process.start()
                    process.join(timeout=timeout_seconds)
                    
                    if process.is_alive():
                        # Timeout occurred
                        process.terminate()
                        process.join()
                        test_details.append({
                            'row': row_idx,
                            'round': round_num,
                            'success': False,
                            'error': f'Timeout after {timeout_seconds}s'
                        })
                    else:
                        # Process completed, check result
                        if not result_queue.empty():
                            result = result_queue.get()
                            if result['success']:
                                successful_tests += 1
                                test_details.append({
                                    'row': row_idx,
                                    'round': round_num,
                                    'success': True,
                                    'result': result.get('result')
                                })
                            else:
                                test_details.append({
                                    'row': row_idx,
                                    'round': round_num,
                                    'success': False,
                                    'error': result.get('error', 'Unknown error')
                                })
                        else:
                            test_details.append({
                                'row': row_idx,
                                'round': round_num,
                                'success': False,
                                'error': 'No result returned from process'
                            })
            
            success_rate = successful_tests / total_tests if total_tests > 0 else 0.0
            
            metadata = {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate,
                'test_details': test_details[:10]  # Only keep first 10 for brevity
            }
            
            return success_rate, metadata
            
        except Exception as e:
            return 0.0, {"error": str(e)}
