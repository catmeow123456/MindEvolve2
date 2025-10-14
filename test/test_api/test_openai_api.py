import os
import anyio
from api import OpenAIConfig, AsyncOpenAILLM

openai_config = {
    "model": "deepseek-v3-250324",
    "timeout": 600
}
llm = AsyncOpenAILLM(OpenAIConfig(**openai_config), os.getenv("OPENAI_BASE_URL"), os.getenv("OPENAI_API_KEY"))

async def main():
    res = await llm.generate("hi")
    print(res)

anyio.run(main)