"""
Model testing functionality for Trust Game
Tests model execution with timeout_sec and parallel sample processing
"""
import csv
import random
import multiprocessing
import os
from typing import Tuple, Dict, Any, List
from concurrent.futures import ProcessPoolExecutor


def _run_policy_with_timeout(model_code: str, state_dict: dict, user_param_dict: dict, 
                              timeout_sec: float, result_queue: multiprocessing.Queue):
    """
    Helper function to run policy in a separate process with timeout_sec
    This runs in a child process
    
    Args:
        model_code: The model code to execute
        state_dict: State dictionary containing round and history
        user_param_dict: User parameter dictionary
        timeout_sec: Timeout value (not used directly, handled by parent)
        result_queue: Queue for returning results
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


def _test_single_round(model_code: str, state_dict: dict, user_param_dict: dict, 
                       timeout_seconds: float, row_idx: int, round_num: int) -> Dict[str, Any]:
    """
    Test a single round in a separate process
    
    Args:
        model_code: The model code to test
        state_dict: State dictionary
        user_param_dict: User parameters
        timeout_seconds: Timeout for execution
        row_idx: Row index for tracking
        round_num: Round number for tracking
        
    Returns:
        Dict containing test result
    """
    # Create a queue for inter-process communication
    result_queue = multiprocessing.Queue()
    
    # Run in separate process with timeout_sec
    process = multiprocessing.Process(
        target=_run_policy_with_timeout,
        args=(model_code, state_dict, user_param_dict, timeout_seconds, result_queue)
    )
    
    process.start()
    process.join(timeout=timeout_seconds)
    
    if process.is_alive():
        # Timeout occurred
        process.terminate()
        process.join()
        return {
            'row': row_idx,
            'round': round_num,
            'success': False,
            'error': f'Timeout after {timeout_seconds}s'
        }
    else:
        # Process completed, check result
        if not result_queue.empty():
            result = result_queue.get()
            if result['success']:
                return {
                    'row': row_idx,
                    'round': round_num,
                    'success': True,
                    'result': result.get('result')
                }
            else:
                return {
                    'row': row_idx,
                    'round': round_num,
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
        else:
            return {
                'row': row_idx,
                'round': round_num,
                'success': False,
                'error': 'No result returned from process'
            }


def test_model_runs_successfully(model_code: str, game_data_path: str,
                                  num_samples: int = 5, 
                                  num_rounds_per_sample: int = 5, 
                                  timeout_seconds: float = 10.0,
                                  parallel: bool = True,
                                  max_workers: int = None) -> Tuple[float, Dict[str, Any]]:
    """
    Test if the model runs successfully on sample data
    
    Args:
        model_code: The model code to test
        game_data_path: Path to the game data CSV file
        num_samples: Number of data rows to sample
        num_rounds_per_sample: Number of rounds to test per sample (max 10)
        timeout_seconds: Timeout for each policy call
        parallel: Whether to run tests in parallel
        max_workers: Maximum number of parallel workers (default: CPU count)
        
    Returns:
        Tuple[float, Dict]: Success rate (0.0-1.0) and metadata with details
    """
    try:
        # Read CSV data
        with open(game_data_path, 'r', encoding='utf-8') as f:
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
        
        # Prepare test cases
        test_cases = []
        for row_idx, row in enumerate(sampled_rows):
            # Extract investor and trustee data
            investor_actions = []
            trustee_actions = []
            
            for i in range(1, 11):  # X1-X10 for investor, X11-X20 for trustee
                try:
                    investor_actions.append(int(row[f'X{i}'].strip().strip('"')))
                    trustee_actions.append(int(row[f'X{i+10}'].strip().strip('"')))
                except (ValueError, KeyError) as e:
                    continue
            
            # Test multiple rounds for this sample
            num_rounds = min(num_rounds_per_sample, len(investor_actions))
            
            for round_num in range(num_rounds):
                # Construct history up to this round
                history = []
                for j in range(round_num):
                    history.append((investor_actions[j], trustee_actions[j]))
                
                state_dict = {
                    'round': round_num,
                    'history': history
                }
                
                test_cases.append({
                    'model_code': model_code,
                    'state_dict': state_dict,
                    'user_param_dict': default_user_params,
                    'timeout_seconds': timeout_seconds,
                    'row_idx': row_idx,
                    'round_num': round_num
                })
        
        # Execute tests (parallel or sequential)
        if parallel and len(test_cases) > 1:
            # Use ProcessPoolExecutor for parallel execution
            if max_workers is None:
                max_workers = min(len(test_cases), os.cpu_count() or 1)
            
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        _test_single_round,
                        tc['model_code'], tc['state_dict'], tc['user_param_dict'],
                        tc['timeout_seconds'], tc['row_idx'], tc['round_num']
                    )
                    for tc in test_cases
                ]
                test_details = [future.result() for future in futures]
        else:
            # Sequential execution
            test_details = []
            for tc in test_cases:
                result = _test_single_round(
                    tc['model_code'], tc['state_dict'], tc['user_param_dict'],
                    tc['timeout_seconds'], tc['row_idx'], tc['round_num']
                )
                test_details.append(result)
        
        # Calculate success rate
        total_tests = len(test_details)
        successful_tests = sum(1 for detail in test_details if detail.get('success', False))
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
