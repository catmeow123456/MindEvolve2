"""
Score extraction functions for Trust Game reviews
"""
import re
from typing import Dict


def extract_scores_from_theoretical_review(review: str) -> Dict[str, float]:
    """
    Extract scores from standardized theoretical review (Reviewer 1)
    Expected format after standardization:
    1. Payoff Calculation: [Yes/Partially/No]
    2. Subjective Utility - Economic Preference: [Yes/Partially/No]
    3. Subjective Utility - Social Preference: [Yes/Partially/No]
    4. Theory of Mind: [Yes/Partially/No]
    5. Planning: [Yes/Partially/No]
    6. Overall Interpretability Score: [XX]
    """
    scores = {}
    
    # Extract Overall Interpretability Score
    pattern = r"Overall Interpretability Score:\s*\[(\d+)\]"
    match = re.search(pattern, review, re.IGNORECASE)
    if match:
        score_value = float(match.group(1))
        if 0 <= score_value <= 100:
            scores["interpretability"] = score_value / 100.0
            scores["overall"] = score_value / 100.0
        else:
            scores["interpretability"] = 0.0
            scores["overall"] = 0.0
    else:
        scores["interpretability"] = 0.0
        scores["overall"] = 0.0
    
    # Extract dimension scores (Yes=1.0, Partially=0.5, No=0.0)
    dimensions = [
        ("Payoff Calculation", "payoff"),
        ("Subjective Utility - Economic Preference", "economic"),
        ("Subjective Utility - Social Preference", "social"),
        ("Theory of Mind", "tom"),
        ("Planning", "planning")
    ]
    
    dimension_scores = []
    for dim_name, dim_key in dimensions:
        pattern = rf"{re.escape(dim_name)}:\s*\[(Yes|Partially|No)\]"
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
        else:
            # If not found, default to 0.0
            scores[dim_key] = 0.0
            dimension_scores.append(0.0)
    
    # Calculate dimension average
    if dimension_scores:
        scores["dimension_average"] = sum(dimension_scores) / len(dimension_scores)
    else:
        scores["dimension_average"] = 0.0
    
    return scores


def extract_scores_from_code_review(review: str) -> Dict[str, float]:
    """
    Extract scores from standardized code quality review (Reviewer 2)
    Expected format after standardization:
    1. Code Clarity and Readability: [XX]
    2. Correctness and Robustness: [XX]
    3. Computational Efficiency: [XX]
    4. Code Organization and Modularity: [XX]
    5. Best Practices Compliance: [XX]
    6. Documentation Quality: [XX]
    7. Overall Code Quality Score: [XX]
    """
    scores = {}
    
    # Extract Overall Code Quality Score
    pattern = r"Overall Code Quality Score:\s*\[(\d+)\]"
    match = re.search(pattern, review, re.IGNORECASE)
    if match:
        score_value = float(match.group(1))
        if 0 <= score_value <= 100:
            scores["overall"] = score_value / 100.0
        else:
            scores["overall"] = 0.0
    else:
        scores["overall"] = 0.0
    
    # Extract dimension scores
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
        pattern = rf"{re.escape(dim_name)}:\s*\[(\d+)\]"
        match = re.search(pattern, review, re.IGNORECASE)
        
        if match:
            score_value = float(match.group(1))
            if 0 <= score_value <= 100:
                score = score_value / 100.0
                dimension_scores.append(score)
                scores[dim_key] = score
            else:
                scores[dim_key] = 0.0
                dimension_scores.append(0.0)
        else:
            # If not found, default to 0.0
            scores[dim_key] = 0.0
            dimension_scores.append(0.0)
    
    # Calculate dimension average
    if dimension_scores:
        scores["dimension_average"] = sum(dimension_scores) / len(dimension_scores)
    else:
        scores["dimension_average"] = 0.0
    
    return scores
