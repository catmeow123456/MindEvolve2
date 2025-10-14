import os
from api.interface_anthropic import AnthropicConfig, AnthropicLLM

anthropic_config = {
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 10000,
    "timeout": 600,
    "thinking_enabled": True,
    "thinking_budget_tokens": 2000
}
llm = AnthropicLLM(
    AnthropicConfig(**anthropic_config), 
    os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"), 
    os.getenv("ANTHROPIC_API_KEY")
)

def main():
    res = llm.generate("写一个贪吃蛇游戏")
    print(res)

if __name__ == "__main__":
    main()
