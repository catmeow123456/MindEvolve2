import os
from dotenv import load_dotenv
from evolution.client import RemoteEvaluatorServerManager

load_dotenv()
# 环境变量的例子
#   HOSTNAME_LIST=cnkunpeng04;cnkunpeng05;cnkunpeng06;cnkunpeng07
# 从环境变量读取主机列表并转换为列表

hostname_list = os.environ.get('HOSTNAME_LIST', '')
ip_pool = [ip.strip() for ip in hostname_list.split(';') if ip.strip()]
print(f"IP 池: {ip_pool}")

client = RemoteEvaluatorServerManager(
    source_dir="core/dictator_game",
    output_dir="tmp/test_client",
    ip_pool=ip_pool,
    key_path="~/.ssh/id_rsa",
)

# 测试代码示例
test_code = """
import numpy as np
from scipy.special import expit
from typing import List, Dict, Tuple

USER_PARAM_CONFIG = {
    # Initial parameter values (customizable): List[float]
    "init_params": [0.5, 0.5, 0.1],
    
    # Parameter bounds (customizable): List[Tuple[float, float]]
    "bounds": [(0.0, 2.0), (0.0, 2.0), (0.0, 1.0)],
    
    # Parameter names (customizable): List[str]
    "names": ["alpha", "beta", "guilt_factor"],
}

def probability_unfair(
    params: List[float],
    cond: int,
    unfair_self: float,
    unfair_other: float,
    fair_self: float = 10,
    fair_other: float = 10
) -> float:
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

"""

with client as manager:
    print(f'可用节点: {manager.available_ips}')
    print(f'资源状态: {manager.get_resource_status()}')
    
    # 测试评估功能
    print("\n测试评估功能...")
    result = manager.execute_evaluation_auto(test_code, timeout_sec=600)
    
    print(f"\n评估结果:")
    print(f"  成功: {result['success']}")
    print(f"  节点: {result.get('ip', 'N/A')}")
    if result['success']:
        print(f"  结果: {result['result']}")
        print(f"  元数据: {result.get('metadata', {})}")
    else:
        print(f"  错误: {result.get('error', 'Unknown')}")
    
    # 检查 tmux 会话
    print("\n检查 tmux 会话...")
    sessions = manager.list_tmux_sessions()
    for ip, session_list in sessions.items():
        print(f"{ip}: {len(session_list)} 个会话")
        for session in session_list[:3]:  # 只显示前3个
            print(f"  - {session}")
