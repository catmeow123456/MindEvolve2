"""
LLM-based reviewers for Trust Game models
Supports parallel execution of multiple reviewers
"""
import os
import concurrent.futures
from typing import Dict, Tuple
from api import AnthropicLLM, AnthropicConfig


class ModelReviewers:
    """Manages LLM-based model reviews with parallel execution support"""
    
    def __init__(self, config: dict, prompt_review_1: str, prompt_review_2: str, 
                 prompt_standardize_theoretical: str, prompt_standardize_code: str):
        """
        Initialize reviewers
        
        Args:
            config: Configuration dict containing reviewer_llm settings
            prompt_review_1: Theoretical review prompt template
            prompt_review_2: Code quality review prompt template
            prompt_standardize_theoretical: Prompt for standardizing theoretical reviews
            prompt_standardize_code: Prompt for standardizing code quality reviews
        """
        self.prompt_review_1 = prompt_review_1
        self.prompt_review_2 = prompt_review_2
        self.prompt_standardize_theoretical = prompt_standardize_theoretical
        self.prompt_standardize_code = prompt_standardize_code
        
        # Create LLM client for reviewers with thinking enabled
        self.review_llm_client = AnthropicLLM(
            AnthropicConfig(**config["reviewer_llm"]),
            base_url=os.getenv("ANTHROPIC_BASE_URL"), 
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    
    def review_model_theoretical(self, model_code: str) -> str:
        """
        Get theoretical review from reviewer 1
        
        Args:
            model_code: The model code to review
            
        Returns:
            Review text from reviewer 1
        """
        content = self.prompt_review_1
        if "{model}" not in content:
            raise ValueError("Prompt review 1 must contain {model} placeholder")
        content = content.replace("{model}", model_code)
        review = self.review_llm_client.generate(content)
        return review
    
    def review_model_code_quality(self, model_code: str) -> str:
        """
        Get code quality review from reviewer 2
        
        Args:
            model_code: The model code to review
            
        Returns:
            Review text from reviewer 2
        """
        content = self.prompt_review_2
        if "{model}" not in content:
            raise ValueError("Prompt review 2 must contain {model} placeholder")
        content = content.replace("{model}", model_code)
        review = self.review_llm_client.generate(content)
        return review
    
    def standardize_review_format(self, review: str, review_type: str) -> str:
        """
        Standardize review format using LLM to ensure consistent score extraction
        
        Args:
            review: The original review text
            review_type: Either 'theoretical' or 'code' to determine which prompt to use
            
        Returns:
            Standardized review text with consistent format
        """
        if review_type == 'theoretical':
            prompt = self.prompt_standardize_theoretical.format(review=review)
        elif review_type == 'code':
            prompt = self.prompt_standardize_code.format(review=review)
        else:
            raise ValueError(f"Invalid review_type: {review_type}. Must be 'theoretical' or 'code'")
        
        try:
            standardized = self.review_llm_client.generate(prompt)
            return standardized
        except Exception as e:
            print(f"Warning: Failed to standardize {review_type} review: {e}")
            return review  # Return original if standardization fails
    
    def review_parallel(self, model_code: str) -> Tuple[str, str]:
        """
        Execute both reviews in parallel for improved performance
        
        Args:
            model_code: The model code to review
            
        Returns:
            Tuple of (theoretical_review, code_quality_review)
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both review tasks
            future_review1 = executor.submit(self.review_model_theoretical, model_code)
            future_review2 = executor.submit(self.review_model_code_quality, model_code)
            
            # Wait for both to complete
            review_1 = future_review1.result()
            review_2 = future_review2.result()
        
        return review_1, review_2
    
    def review_and_standardize_parallel(self, model_code: str) -> Tuple[str, str, str, str]:
        """
        Execute both reviews and standardization in parallel for improved performance
        
        Args:
            model_code: The model code to review
            
        Returns:
            Tuple of (theoretical_review, code_quality_review, 
                     standardized_theoretical, standardized_code)
        """
        # First get both reviews in parallel
        review_1, review_2 = self.review_parallel(model_code)
        
        # Then standardize both in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_std1 = executor.submit(self.standardize_review_format, review_1, 'theoretical')
            future_std2 = executor.submit(self.standardize_review_format, review_2, 'code')
            
            standardized_1 = future_std1.result()
            standardized_2 = future_std2.result()
        
        return review_1, review_2, standardized_1, standardized_2
