import asyncio
from typing import Optional, Union, Literal, override
from dataclasses import dataclass, asdict
from openai import AsyncOpenAI, OpenAI, NotGiven, NOT_GIVEN
from api.base import LLMInterface

import datetime
import time

def get_time() -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S.%f")

@dataclass
class OpenAIConfig:
    model: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: int = 4096
    reasoning_effort: Optional[Literal["minimal", "low", "medium", "high"]] = None  # For OpenAI o-series models
    timeout_sec: int = 60
    retries: int = 3
    retry_delay: int = 5

    def to_json(self) -> dict:
        return asdict(self)

class OpenAILLM(LLMInterface):
    config: OpenAIConfig
    client: OpenAI

    def __init__(self, model_config: OpenAIConfig, base_url: str, api_key: str):
        self.config = model_config
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    @override
    def generate(self, prompt: str, **kwargs: any) -> str:
        message_list = [{"role": "user", "content": prompt}]
        res = self._generate(messages=message_list, **kwargs)
        if not res.content:
            raise ValueError("The generation result is empty, and no valid content can be obtained.")
        return res.content

    def _generate(self, messages, **kwargs: any):
        begin_time = get_time()
        print(f"{begin_time} - begin request, timeout_sec={self.config.timeout_sec}")
        for attempt in range(self.config.retries):
            try:
                kwargs = {
                    "model": self.config.model,
                    "messages": messages,
                    "stream": False
                }
                if self.config.temperature is not None:
                    kwargs["temperature"] = self.config.temperature
                if self.config.max_tokens is not None:
                    kwargs["max_tokens"] = self.config.max_tokens
                if self.config.top_p is not None:
                    kwargs["top_p"] = self.config.top_p
                if self.config.timeout_sec:
                    kwargs["timeout"] = self.config.timeout_sec
                if self.config.model.startswith("o") and self.config.reasoning_effort is not None:
                    kwargs["reasoning_effort"] = self.config.reasoning_effort
                completion = self.client.chat.completions.create(**kwargs)
                result_message = completion.choices[0].message
                return result_message
            except Exception as e:
                print(f"{get_time()} - Attempt {attempt + 1} failed: {e},begin_time={begin_time}", flush=True)
                if attempt < self.config.retries - 1:
                    time.sleep(self.config.retry_delay)
                raise e


class AsyncOpenAILLM(LLMInterface):
    config: OpenAIConfig
    client: AsyncOpenAI

    def __init__(self, model_config: OpenAIConfig, base_url: str, api_key: str):
        self.config = model_config
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    @override
    async def generate(self, prompt: str, **kwargs: any) -> str:
        message_list = [{"role": "user", "content": prompt}]
        res = await self._generate(messages=message_list, **kwargs)
        if not res.content:
            raise ValueError("The generation result is empty, and no valid content can be obtained.")
        return res.content

    async def _generate(self, messages, **kwargs: any):
        begin_time = get_time()
        print(f"{begin_time} - begin request, timeout_sec={self.config.timeout_sec}")
        for attempt in range(self.config.retries):
            try:
                kwargs = {
                    "model": self.config.model,
                    "messages": messages,
                    "stream": False
                }
                if self.config.temperature is not None:
                    kwargs["temperature"] = self.config.temperature
                if self.config.max_tokens is not None:
                    kwargs["max_tokens"] = self.config.max_tokens
                if self.config.top_p is not None:
                    kwargs["top_p"] = self.config.top_p
                if self.config.timeout_sec:
                    kwargs["timeout"] = self.config.timeout_sec
                if self.config.model.startswith("o") and self.config.reasoning_effort is not None:
                    kwargs["reasoning_effort"] = self.config.reasoning_effort
                completion = await self.client.chat.completions.create(**kwargs)
                result_message = completion.choices[0].message
                return result_message
            except Exception as e:
                print(f"{get_time()} - Attempt {attempt + 1} failed: {e},begin_time={begin_time}", flush=True)
                if attempt < self.config.retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                raise e
