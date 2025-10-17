"""
LiteLLM unified interface for multiple LLM providers
"""

import time
import asyncio
from typing import Optional, Any, Dict, override
from dataclasses import dataclass, asdict
import datetime

from litellm import completion, acompletion
from api.base import LLMInterface


def get_time() -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S.%f")


@dataclass
class LiteLLMConfig:
    """Configuration for LiteLLM interface
    
    API keys and base URLs are read from environment variables:
    - OPENAI_API_KEY, OPENAI_API_BASE
    - ANTHROPIC_API_KEY, ANTHROPIC_API_BASE
    - And other provider-specific environment variables
    
    Args:
        model: Model name (e.g., "gpt-4", "claude-3-5-sonnet-20241022", "gemini/gemini-pro")
        temperature: Sampling temperature (0.0 to 2.0)
        top_p: Nucleus sampling parameter
        max_tokens: Maximum tokens to generate
        timeout_sec: Request timeout_sec in seconds
        retries: Number of retry attempts on failure
        retry_delay: Delay between retries in seconds
        extra_params: Additional parameters to pass to LiteLLM
    """
    model: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: int = 4096
    timeout_sec: int = 60
    retries: int = 3
    retry_delay: int = 5
    extra_params: Optional[Dict[str, Any]] = None

    def to_json(self) -> dict:
        return asdict(self)


class LiteLLM(LLMInterface):
    """Synchronous LiteLLM interface"""
    
    config: LiteLLMConfig
    api_base: str
    api_key: str

    def __init__(self, model_config: LiteLLMConfig, api_base: str, api_key: str):
        """Initialize LiteLLM interface
        
        Args:
            model_config: Model configuration
            api_base: Custom API base URL
            api_key: API key
        """
        self.config = model_config
        self.api_base = api_base
        self.api_key = api_key
        if self.api_base.endswith('/'):
            self.api_base = self.api_base[:-1]
        if 'gemini' in self.config.model:
            if not self.api_base.endswith("/v1beta"):
                self.api_base = self.api_base + '/v1beta'
        elif 'claude' not in self.config.model:
            if not self.api_base.endswith("/v1"):
                self.api_base = self.api_base + '/v1'

    @override
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt
        
        Args:
            prompt: Input prompt text
            **kwargs: Additional parameters to override config
            
        Returns:
            Generated text response
        """
        message_list = [{"role": "user", "content": prompt}]
        response = self._generate(messages=message_list, **kwargs)
        
        # Extract content from response
        if hasattr(response, 'choices') and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, 'content') and message.content:
                return message.content
        
        raise ValueError("The generation result is empty, and no valid content can be obtained.")

    def _generate(self, messages: list, **kwargs: Any):
        """Internal method to call LiteLLM completion
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters to override config
            
        Returns:
            LiteLLM completion response
        """
        begin_time = get_time()
        print(f"{begin_time} - begin request, timeout_sec={self.config.timeout_sec}")
        
        for attempt in range(self.config.retries):
            try:
                # Build request parameters
                params = {
                    "model": self.config.model,
                    "messages": messages,
                    "timeout": self.config.timeout_sec,
                }
                
                # Add API base and key if provided
                if self.api_base is not None:
                    params["api_base"] = self.api_base
                if self.api_key is not None:
                    params["api_key"] = self.api_key
                
                # Add optional parameters from config
                if self.config.temperature is not None:
                    params["temperature"] = self.config.temperature
                if self.config.top_p is not None:
                    params["top_p"] = self.config.top_p
                if self.config.max_tokens is not None:
                    params["max_tokens"] = self.config.max_tokens
                
                # Add extra parameters if specified
                if self.config.extra_params:
                    params.update(self.config.extra_params)
                
                # Override with kwargs
                params.update(kwargs)
                
                # Call LiteLLM completion
                response = completion(**params)
                return response
                
            except Exception as e:
                print(f"{get_time()} - Attempt {attempt + 1} failed: {e}, begin_time={begin_time}", flush=True)
                if attempt < self.config.retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    raise e


class AsyncLiteLLM(LLMInterface):
    """Asynchronous LiteLLM interface"""
    
    config: LiteLLMConfig
    api_base: Optional[str]
    api_key: Optional[str]

    def __init__(self, model_config: LiteLLMConfig, api_base: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize AsyncLiteLLM interface
        
        Args:
            model_config: Model configuration
            api_base: Custom API base URL (optional, overrides environment variables)
            api_key: API key (optional, overrides environment variables)
        """
        self.config = model_config
        self.api_base = api_base
        self.api_key = api_key

        if self.api_base.endswith('/'):
            self.api_base = self.api_base[:-1]
        if 'gemini' in self.config.model:
            if not self.api_base.endswith("/v1beta"):
                self.api_base = self.api_base + '/v1beta'
        elif 'claude' not in self.config.model:
            if not self.api_base.endswith("/v1"):
                self.api_base = self.api_base + '/v1'

    @override
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt asynchronously
        
        Args:
            prompt: Input prompt text
            **kwargs: Additional parameters to override config
            
        Returns:
            Generated text response
        """
        message_list = [{"role": "user", "content": prompt}]
        response = await self._generate(messages=message_list, **kwargs)
        # DEBUG: print(response)
        # Extract content from response
        if hasattr(response, 'choices') and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, 'content') and message.content:
                return message.content
        
        raise ValueError("The generation result is empty, and no valid content can be obtained.")

    async def _generate(self, messages: list, **kwargs: Any):
        """Internal method to call LiteLLM async completion
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters to override config
            
        Returns:
            LiteLLM completion response
        """
        begin_time = get_time()
        print(f"{begin_time} - begin async request, timeout_sec={self.config.timeout_sec}")
        
        for attempt in range(self.config.retries):
            try:
                # Build request parameters
                params = {
                    "model": self.config.model,
                    "messages": messages,
                    "timeout": self.config.timeout_sec,
                }
                
                # Add API base and key if provided
                if self.api_base is not None:
                    params["api_base"] = self.api_base
                if self.api_key is not None:
                    params["api_key"] = self.api_key
                
                # Add optional parameters from config
                if self.config.temperature is not None:
                    params["temperature"] = self.config.temperature
                if self.config.top_p is not None:
                    params["top_p"] = self.config.top_p
                if self.config.max_tokens is not None:
                    params["max_tokens"] = self.config.max_tokens
                
                # Add extra parameters if specified
                if self.config.extra_params:
                    params.update(self.config.extra_params)
                
                # Override with kwargs
                params.update(kwargs)
                
                # Call LiteLLM async completion
                response = await acompletion(**params)
                return response
                
            except Exception as e:
                print(f"{get_time()} - Attempt {attempt + 1} failed: {e}, begin_time={begin_time}", flush=True)
                if attempt < self.config.retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    raise e
