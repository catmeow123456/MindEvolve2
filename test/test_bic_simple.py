"""
Simple test for BIC calculator functionality
"""
from core.trust_game.bic_calculator import calculate_bic_score

# Simple test model code
test_model_code = """
from typing import List, Tuple
import numpy as np

class UserParameter:
    def __init__(self, inequalityAversion, riskAversion, theoryOfMindSophistication,
                 planning, irritability, irritationAwareness, inverseTemperature):
        self.inequalityAversion = inequalityAversion
        self.riskAversion = riskAversion
        self.theoryOfMindSophistication = theoryOfMindSophistication
        self.planning = planning
        self.irritability = irritability
        self.irritationAwareness = irritationAwareness
        self.inverseTemperature = inverseTemperature

class State:
    def __init__(self, round: int, history: List[Tuple[int, int]]):
        self.round = round
        self.history = history

def policy(user_parameter: UserParameter, state: State) -> List[float]:
    # Simple uniform distribution for testing
    return [0.2, 0.2, 0.2, 0.2, 0.2]
"""

# Test configuration
test_config = {
    'max_workers': 64,  # Use fewer workers for testing
    'BIC_calc_timeout': 600  # 600 seconds (10 minutes) for testing with 824 experiments
}

if __name__ == "__main__":
    print("测试 BIC 计算功能...")
    print("=" * 50)
    
    try:
        bic_score, metadata = calculate_bic_score(
            test_model_code,
            "core/trust_game/main/BaseNSPNTrust.csv",
            test_config
        )
        
        print("\n" + "=" * 50)
        print("测试成功!")
        print(f"BIC 分数: {bic_score:.4f}")
        print(f"原始 BIC: {metadata.get('raw_bic', 'N/A')}")
        print(f"参数数量: {metadata.get('num_parameters', 'N/A')}")
        print(f"平均 NLL: {metadata.get('mean_nll', 'N/A')}")
        
        if 'error' in metadata:
            print(f"错误: {metadata['error']}")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
