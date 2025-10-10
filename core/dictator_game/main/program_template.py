import numpy as np
from scipy.special import expit
from typing import List, Dict, Tuple

# ================================
# 1. Model Parameter Configuration
# ================================
USER_PARAM_CONFIG = {
    # Initial parameter values (customizable): List[float]
    "init_params": [0.5, 0.5, 0.1],
    
    # Parameter bounds (customizable): List[Tuple[float, float]]
    "bounds": [(0.0, 2.0), (0.0, 2.0), (0.0, 1.0)],
    
    # Parameter names (customizable): List[str]
    "names": ["alpha", "beta", "guilt_factor"],
}

# ================================
# 2. Core Prediction Function
# ================================
def probability_unfair(
    params: List[float],
    cond: int,
    unfair_self: float,
    unfair_other: float,
    fair_self: float = 10,
    fair_other: float = 10
) -> float:
    """
    Compute the probability of choosing the 'unfair' option under a given condition.
    
    Parameters:
    - params: List of model parameters
    - cond: Current condition index (0-3), 
            0: Self_Pain, 1: Self_NoPain, 2: Other_Pain, 3: Other_NoPain
    - unfair_self / unfair_other: Payoffs for self/other in the unfair option
    - fair_self / fair_other: Payoffs for self/other in the fair option
    
    Returns:
    - prob_unfair: Probability of choosing the unfair option (range: 0 to 1)
    """
    alpha, beta, guilt_factor = params
    
    # Calculate utility for unfair option
    unfair_utility = alpha * unfair_self - beta * max(0, unfair_self - unfair_other)
    
    # Calculate utility for fair option
    fair_utility = alpha * fair_self - beta * max(0, fair_self - fair_other)
    
    # Apply guilt factor based on condition
    if cond == 0:  # Self_Pain - high guilt
        unfair_utility -= guilt_factor * 2.0
    elif cond == 1:  # Self_NoPain - medium guilt
        unfair_utility -= guilt_factor * 1.0
    elif cond == 2:  # Other_Pain - low guilt
        unfair_utility -= guilt_factor * 0.5
    # cond == 3: Other_NoPain - no guilt adjustment
    
    # Convert to probability using logistic function
    utility_diff = unfair_utility - fair_utility
    prob_unfair = expit(utility_diff)
    
    return prob_unfair
