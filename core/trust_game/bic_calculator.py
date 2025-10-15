"""
BIC (Bayesian Information Criterion) Calculator for Trust Game Models
Calculates BIC score by fitting model to experimental data
"""
import csv
import numpy as np
import multiprocessing
from typing import List, Tuple, Dict, Any, Generator
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError
import warnings

warnings.filterwarnings("ignore")


class ExperimentData:
    """Container for a single experiment's trust game data"""
    def __init__(self, ID: str, trustGameData: List[Tuple[int, int]]):
        self.ID = ID
        self.trustGameData = trustGameData


def gen_user_para() -> Generator[Dict[str, Any], None, None]:
    """
    Generate all possible UserParameter combinations
    Total: 3 × 8 × 5 × 4 × 5 × 5 × 4 = 48,000 combinations
    """
    inequalityAversion_values = [0, 0.4, 1]
    riskAversion_values = [0.4, 0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8]
    theoryOfMindSophistication_values = [0, 1, 2, 3, 4]
    planning_values = [1, 2, 3, 4]
    irritability_values = [0, 0.25, 0.5, 0.75, 1]
    irritationAwareness_values = [0, 1, 2, 3, 4]
    inverseTemperature_values = [1/4, 1/3, 1/2, 1/1]
    
    for ia in inequalityAversion_values:
        for ra in riskAversion_values:
            for tom in theoryOfMindSophistication_values:
                for plan in planning_values:
                    for irr in irritability_values:
                        for irr_aware in irritationAwareness_values:
                            for inv_temp in inverseTemperature_values:
                                yield {
                                    'inequalityAversion': ia,
                                    'riskAversion': ra,
                                    'theoryOfMindSophistication': tom,
                                    'planning': plan,
                                    'irritability': irr,
                                    'irritationAwareness': irr_aware,
                                    'inverseTemperature': inv_temp
                                }


def load_experiment_data(csv_path: str) -> List[ExperimentData]:
    """
    Load experiment data from CSV file
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of ExperimentData objects
    """
    data = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            next(reader)  # Skip header
            
            for row in reader:
                if row:  # Ensure row is not empty
                    experiment_id = row[0].strip().strip('"')
                    trust_game_data = []
                    
                    # Extract X1-X10 (investor) and X11-X20 (trustee)
                    for i in range(1, 11):
                        try:
                            investor_action = int(row[i].strip().strip('"'))
                            trustee_action = int(row[i + 10].strip().strip('"'))
                            trust_game_data.append((investor_action, trustee_action))
                        except (ValueError, IndexError):
                            continue
                    
                    if trust_game_data:  # Only add if we have valid data
                        data.append(ExperimentData(ID=experiment_id, trustGameData=trust_game_data))
    except Exception as e:
        raise ValueError(f"Failed to load experiment data from {csv_path}: {e}")
    
    return data


def _evaluate_nll_single(args: Tuple[ExperimentData, str]) -> Tuple[str, float, Dict[str, Any]]:
    """
    Evaluate NLL for a single experiment data
    This function is designed to be called in a separate process
    
    Args:
        args: Tuple of (experiment_data, model_code)
        
    Returns:
        Tuple of (experiment_id, nll, best_parameters)
    """
    data_i, model_code = args
    
    try:
        # Execute model code in isolated namespace
        namespace = {}
        exec(model_code, namespace)
        
        if 'policy' not in namespace:
            return (data_i.ID, 1e9, {"error": "policy function not found"})
        
        policy_func = namespace['policy']
        
        # Get classes from namespace or define them
        if 'UserParameter' in namespace:
            UserParamClass = namespace['UserParameter']
        else:
            class UserParamClass:
                def __init__(self, inequalityAversion, riskAversion, theoryOfMindSophistication,
                           planning, irritability, irritationAwareness, inverseTemperature):
                    self.inequalityAversion = inequalityAversion
                    self.riskAversion = riskAversion
                    self.theoryOfMindSophistication = theoryOfMindSophistication
                    self.planning = planning
                    self.irritability = irritability
                    self.irritationAwareness = irritationAwareness
                    self.inverseTemperature = inverseTemperature
        
        if 'State' in namespace:
            StateClass = namespace['State']
        else:
            class StateClass:
                def __init__(self, round: int, history: List[Tuple[int, int]]):
                    self.round = round
                    self.history = history
        
        # Find best parameters by minimizing NLL
        best_nll = 1e9
        best_para = None
        
        for para_dict in gen_user_para():
            try:
                user_param = UserParamClass(**para_dict)
                nll = 0.0
                
                # Calculate NLL for all rounds
                for j in range(len(data_i.trustGameData)):
                    state = StateClass(j, data_i.trustGameData[:j])
                    
                    # Call policy function
                    action_prob = policy_func(user_param, state)
                    
                    # Validate action probabilities
                    if not isinstance(action_prob, (list, tuple)) or len(action_prob) != 5:
                        raise ValueError(f"Invalid action_prob format: {action_prob}")
                    
                    action_prob = [float(p) for p in action_prob]
                    
                    if not abs(sum(action_prob) - 1.0) < 1e-6:
                        raise ValueError(f"Action probabilities don't sum to 1: {sum(action_prob)}")
                    
                    if any(p < 0 for p in action_prob):
                        raise ValueError(f"Negative probabilities: {action_prob}")
                    
                    # Map investor action to index: 0->0, 5->1, 10->2, 15->3, 20->4
                    investor_action = data_i.trustGameData[j][0]
                    action_idx = (investor_action + 2) // 5
                    
                    # Add negative log likelihood
                    nll += -np.log(action_prob[action_idx] + 1e-18)
                
                nll = max(nll, 0.0)
                
                # Update best parameters
                if nll < best_nll:
                    best_nll = nll
                    best_para = para_dict
                    
            except Exception as e:
                # Skip this parameter combination if it fails
                continue
        
        if best_para is None:
            return (data_i.ID, 1e9, {"error": "No valid parameter combination found"})
        
        return (data_i.ID, best_nll, best_para)
        
    except Exception as e:
        return (data_i.ID, 1e9, {"error": str(e)})


def calculate_bic_score(model_code: str, game_data_path: str, config: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate BIC score for a model
    
    Args:
        model_code: The model code to evaluate
        game_data_path: Path to the game data CSV file
        config: Configuration dict containing max_workers and BIC_calc_timeout
        
    Returns:
        Tuple of (bic_score, metadata)
        - bic_score: Normalized BIC score in [0, 1], where 1 is best (BIC=18) and 0 is worst (BIC=30)
        - metadata: Dict containing calculation details and any errors
    """
    try:
        # Get configuration parameters
        max_workers = config.get('max_workers', 128)
        timeout = config.get('BIC_calc_timeout', 300)
        
        # Load experiment data
        print(f"加载实验数据: {game_data_path}")
        experiment_data = load_experiment_data(game_data_path)
        n_experiments = len(experiment_data)
        print(f"加载了 {n_experiments} 个实验数据")
        
        if n_experiments == 0:
            return 0.0, {"error": "No experiment data loaded"}
        
        # Prepare arguments for parallel processing
        args_list = [(data_i, model_code) for data_i in experiment_data]
        
        # Calculate NLL for each experiment in parallel
        print(f"开始并行计算 NLL (max_workers={max_workers}, total_timeout={timeout}s)...")
        print(f"预计每个实验需要遍历 48,000 种参数组合...")
        results_list = []
        
        # Calculate per-experiment timeout based on total timeout and number of parallel batches
        # Each batch processes max_workers experiments in parallel
        num_batches = max(1, (n_experiments + max_workers - 1) // max_workers)
        per_experiment_timeout = max(60, timeout / num_batches)  # At least 60s per experiment
        print(f"每个实验超时时间: {per_experiment_timeout:.1f}s (共 {num_batches} 批次)")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            try:
                futures = [executor.submit(_evaluate_nll_single, args) for args in args_list]
                
                completed = 0
                for i, future in enumerate(futures):
                    try:
                        exp_id, nll, params = future.result(timeout=per_experiment_timeout)
                        results_list.append((exp_id, nll, params))
                        completed += 1
                        if (i + 1) % 10 == 0 or (i + 1) == n_experiments:
                            print(f"进度: {completed}/{n_experiments} ({completed/n_experiments*100:.1f}%)")
                        
                    except FuturesTimeoutError:
                        print(f"实验 {i+1}/{n_experiments} 超时（>{per_experiment_timeout}s），使用默认 NLL=1e9")
                        results_list.append(("unknown", 1e9, {}))
                    except Exception as e:
                        print(f"实验 {i+1}/{n_experiments} 计算失败: {e}，使用默认 NLL=1e9")
                        results_list.append(("unknown", 1e9, {}))
                        
            except Exception as e:
                print(f"并行计算出错: {e}")
                return 0.0, {"error": f"Parallel computation failed: {e}"}
        
        print(f"NLL 计算完成，共 {len(results_list)} 个结果")
        
        # Calculate parameter count (para_num) by checking which parameters vary across experiments
        # Parameters order: inequalityAversion, riskAversion, theoryOfMindSophistication, 
        #                   planning, irritability, irritationAwareness, inverseTemperature
        param_names = ['inequalityAversion', 'riskAversion', 'theoryOfMindSophistication', 
                       'planning', 'irritability', 'irritationAwareness', 'inverseTemperature']
        
        para_num = 0
        meaningful_params = []
        
        for param_name in param_names:
            # Check if this parameter varies across experiments
            first_value = None
            meaningful = False
            
            for exp_id, nll, params in results_list:
                if not params or "error" in params:
                    continue
                
                param_value = params.get(param_name)
                if param_value is None:
                    continue
                
                if first_value is None:
                    first_value = param_value
                elif param_value != first_value:
                    meaningful = True
                    break
            
            if meaningful:
                para_num += 1
                meaningful_params.append(param_name)
        
        print(f"有意义的参数数量: {para_num}")
        print(f"有意义的参数: {meaningful_params}")
        
        # Extract NLL values
        nll_values = [nll for exp_id, nll, params in results_list]
        mean_nll = np.mean(nll_values)
        
        # Calculate BIC using the formula from reference code:
        # BIC = 2 * mean(NLL) + para_num * (log(10) - log(2*pi))
        raw_bic = 2 * mean_nll + para_num * (np.log(10) - np.log(2 * np.pi))
        
        print(f"BIC 计算: para_num={para_num}, mean(NLL)={mean_nll:.2f}")
        print(f"原始 BIC = {raw_bic:.2f}")
        
        # Normalize BIC to [0, 1]: 18 -> 1.0, 30 -> 0.0
        # Linear interpolation: score = (30 - BIC) / (30 - 18)
        bic_score = max(0.0, min(1.0, (30.0 - raw_bic) / 12.0))
        
        print(f"归一化 BIC 分数 = {bic_score:.4f}")
        
        metadata = {
            "raw_bic": float(raw_bic),
            "num_parameters": para_num,
            "meaningful_parameters": meaningful_params,
            "mean_nll": float(mean_nll),
            "nll_values": [float(x) for x in nll_values[:10]],  # Keep first 10 for brevity
            "best_parameters_sample": {exp_id: params for exp_id, nll, params in results_list[:3]}  # Sample 3
        }
        
        return bic_score, metadata
        
    except Exception as e:
        print(f"BIC 计算失败: {e}")
        return 0.0, {"error": str(e)}
