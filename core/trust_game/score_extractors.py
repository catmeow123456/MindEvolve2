"""
Score extraction functions for Trust Game reviews
"""
import re
from typing import Dict


def extract_scores_from_theoretical_review(review: str) -> Dict[str, float]:
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


def extract_scores_from_code_review(review: str) -> Dict[str, float]:
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
