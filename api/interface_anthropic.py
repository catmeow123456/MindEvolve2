import time
import asyncio
from typing import Optional, Union, Literal, override
from dataclasses import dataclass, asdict
from anthropic import Anthropic, AsyncAnthropic
from api.base import LLMInterface

import datetime

def get_time() -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S.%f")

@dataclass
class AnthropicConfig:
    model: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: int = 4096
    thinking_enabled: bool = True  # Enable extended thinking
    thinking_budget_tokens: int = 1024  # Budget for thinking tokens
    timeout: int = 60
    retries: int = 3
    retry_delay: int = 5

    def to_json(self) -> dict:
        return asdict(self)

class AnthropicLLM(LLMInterface):
    config: AnthropicConfig
    client: Anthropic

    def __init__(self, model_config: AnthropicConfig, base_url: str, api_key: str):
        self.config = model_config
        self.client = Anthropic(base_url=base_url, api_key=api_key)

    @override
    def generate(self, prompt: str, **kwargs: any) -> str:
        message_list = [{"role": "user", "content": prompt}]
        res = self._generate(messages=message_list, **kwargs)
        if not res.content:
            raise ValueError("The generation result is empty, and no valid content can be obtained.")
        # Extract text from response content
        text_content = ""
        for block in res.content:
            if hasattr(block, 'text'):
                text_content += block.text
        if not text_content:
            raise ValueError("No text content found in the response.")
        return text_content

    def _generate(self, messages, **kwargs: any):
        begin_time = get_time()
        print(f"{begin_time} - begin request, timeout={self.config.timeout}")
        for attempt in range(self.config.retries):
            try:
                kwargs = {
                    "model": self.config.model,
                    "messages": messages,
                    "max_tokens": self.config.max_tokens,
                }
                
                if self.config.temperature is not None:
                    kwargs["temperature"] = self.config.temperature
                if self.config.top_p is not None:
                    kwargs["top_p"] = self.config.top_p
                if self.config.timeout:
                    kwargs["timeout"] = self.config.timeout
                
                # Add thinking parameter if enabled
                if self.config.thinking_enabled:
                    kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": self.config.thinking_budget_tokens,
                    }
                
                message = self.client.messages.create(**kwargs)
                return message
            except Exception as e:
                print(f"{get_time()} - Attempt {attempt + 1} failed: {e}, begin_time={begin_time}", flush=True)
                if attempt < self.config.retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    raise e


class AsyncAnthropicLLM(LLMInterface):
    config: AnthropicConfig
    client: AsyncAnthropic

    def __init__(self, model_config: AnthropicConfig, base_url: str, api_key: str):
        self.config = model_config
        self.client = AsyncAnthropic(base_url=base_url, api_key=api_key)

    @override
    async def generate(self, prompt: str, **kwargs: any) -> str:
        message_list = [{"role": "user", "content": prompt}]
        res = await self._generate(messages=message_list, **kwargs)
        if not res.content:
            raise ValueError("The generation result is empty, and no valid content can be obtained.")
        # Extract text from response content
        text_content = ""
        for block in res.content:
            if hasattr(block, 'text'):
                text_content += block.text
        if not text_content:
            raise ValueError("No text content found in the response.")
        return text_content

    async def _generate(self, messages, **kwargs: any):
        begin_time = get_time()
        print(f"{begin_time} - begin async request, timeout={self.config.timeout}")
        for attempt in range(self.config.retries):
            try:
                kwargs = {
                    "model": self.config.model,
                    "messages": messages,
                    "max_tokens": self.config.max_tokens,
                }
                
                if self.config.temperature is not None:
                    kwargs["temperature"] = self.config.temperature
                if self.config.top_p is not None:
                    kwargs["top_p"] = self.config.top_p
                if self.config.timeout:
                    kwargs["timeout"] = self.config.timeout
                
                # Add thinking parameter if enabled
                if self.config.thinking_enabled:
                    kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": self.config.thinking_budget_tokens,
                    }
                
                message = await self.client.messages.create(**kwargs)
                return message
            except Exception as e:
                print(f"{get_time()} - Attempt {attempt + 1} failed: {e}, begin_time={begin_time}", flush=True)
                if attempt < self.config.retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    raise e
