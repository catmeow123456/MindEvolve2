"""
Test LiteLLM API interface
"""

import os
import asyncio
from dotenv import load_dotenv
from api.interface_litellm import LiteLLM, AsyncLiteLLM, LiteLLMConfig

# Load environment variables from .env file
load_dotenv()

# Get LiteLLM configuration from environment
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")


def test_litellm_openai():
    """Test LiteLLM with OpenAI model (gpt-4)"""
    config = LiteLLMConfig(
        model="openai/deepseek-v3-250324",
        max_tokens=100
    )
    
    llm = LiteLLM(
        model_config=config,
        api_base=LITELLM_BASE_URL + "/v1",
        api_key=LITELLM_API_KEY
    )
    response = llm.generate("Hello, how are you?")
    print(f"OpenAI Response: {response}")
    assert response is not None
    assert len(response) > 0


def test_litellm_anthropic():
    """Test LiteLLM with Anthropic model (Claude)"""
    config = LiteLLMConfig(
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        max_tokens=100
    )
    
    llm = LiteLLM(
        model_config=config,
        api_base=LITELLM_BASE_URL,
        api_key=LITELLM_API_KEY
    )
    response = llm.generate("Hello, how are you?")
    print(f"Anthropic Response: {response}")
    assert response is not None
    assert len(response) > 0


def test_litellm_gemini():
    """Test LiteLLM with Gemini model"""
    config = LiteLLMConfig(
        model="gemini/gemini-2.5-flash",
        temperature=0.7,
        max_tokens=100
    )
    
    llm = LiteLLM(
        model_config=config,
        api_base=LITELLM_BASE_URL + "/v1beta",
        api_key=LITELLM_API_KEY
    )
    response = llm.generate("Hello, how are you?")
    print(f"Gemini Response: {response}")
    assert response is not None
    assert len(response) > 0


async def test_async_litellm():
    """Test AsyncLiteLLM interface"""
    config = LiteLLMConfig(
        model="gpt-4.1",
        temperature=0.7,
        max_tokens=100
    )
    
    llm = AsyncLiteLLM(
        model_config=config,
        api_base=LITELLM_BASE_URL + "/v1",
        api_key=LITELLM_API_KEY
    )
    response = await llm.generate("Hello, how are you?")
    print(f"Async Response: {response}")
    assert response is not None
    assert len(response) > 0

if __name__ == "__main__":
    print("=== LiteLLM API Tests ===\n")
    print(f"LITELLM_BASE_URL: {LITELLM_BASE_URL}")
    print(f"LITELLM_API_KEY: {'Set' if LITELLM_API_KEY else 'Not set'}\n")
    
    # Run sync tests
    print("\nTesting Gemini...")
    test_litellm_gemini()
    
    print("Testing OpenAI...")
    test_litellm_openai()
    
    print("\nTesting Anthropic (Claude)...")
    test_litellm_anthropic()
    
    # Run async test
    print("\nTesting async interface...")
    asyncio.run(test_async_litellm())
    
    print("\n✅ All tests defined (uncomment to run)")
