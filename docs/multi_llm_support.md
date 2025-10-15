# 多 LLM Provider 支持文档

## 概述

本项目现已支持三种不同的 LLM provider：
1. **OpenAI** - 包括 GPT 系列和 o-series 模型
2. **Anthropic** - Claude 系列模型
3. **LiteLLM** - 统一接口，支持多个 LLM 提供商（如 Gemini、Claude、GPT 等）

## 配置方式

在 YAML 配置文件中，通过 `provider` 字段指定使用的 LLM 类型：

### 1. OpenAI 配置示例

```yaml
llm:
  provider: "openai"  # 指定使用 OpenAI
  model: "o3-2025-04-16"
  temperature: 0.7
  max_tokens: 4096
  reasoning_effort: "high"  # OpenAI o-series 模型特有参数
  timeout: 60
  retries: 3
  retry_delay: 5
```

**环境变量：**
- `OPENAI_BASE_URL` - OpenAI API 基础 URL
- `OPENAI_API_KEY` - OpenAI API 密钥

**特有参数：**
- `reasoning_effort`: 推理努力程度（仅用于 o-series 模型），可选值：`"minimal"`, `"low"`, `"medium"`, `"high"`

### 2. Anthropic 配置示例

```yaml
llm:
  provider: "anthropic"  # 指定使用 Anthropic
  model: "claude-sonnet-4-5-20250929"
  temperature: 1    # 开启 thinking 时，temperature 必须设置为 1
  max_tokens: 4096
  thinking_enabled: true  # Anthropic 特有：启用扩展思考
  thinking_budget_tokens: 1024  # Anthropic 特有：思考令牌预算
  timeout: 60
  retries: 3
  retry_delay: 5
```

**环境变量：**
- `ANTHROPIC_BASE_URL` - Anthropic API 基础 URL（可选，默认为 `https://api.anthropic.com`）
- `ANTHROPIC_API_KEY` - Anthropic API 密钥

**特有参数：**
- `thinking_enabled`: 是否启用扩展思考功能（默认 `true`）
- `thinking_budget_tokens`: 思考令牌预算（默认 `1024`）

### 3. LiteLLM 配置示例

```yaml
llm:
  provider: "litellm"  # 指定使用 LiteLLM
  model: "gemini/gemini-2.5-flash"  # 可以是任何 LiteLLM 支持的模型
  temperature: 0.7
  max_tokens: 4096
  timeout: 60
  retries: 3
  retry_delay: 5
  # extra_params:  # 可选：传递给 LiteLLM 的额外参数
  #   custom_param: "value"
```

**环境变量：**
LiteLLM 会自动从环境变量读取不同 provider 的配置：
- `OPENAI_API_KEY`, `OPENAI_API_BASE`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_API_BASE`
- `GEMINI_API_KEY`
- 等等...

**特有参数：**
- `extra_params`: 字典类型，可以传递给 LiteLLM 的额外参数

## 默认行为

如果在配置文件中不指定 `provider` 字段，系统将默认使用 `"openai"` 作为 provider。

## 向后兼容性

现有的配置文件将继续正常工作。系统会自动为它们添加默认的 `provider: "openai"` 字段。

## 架构说明

### 类层次结构

```
LLMInterface (抽象基类)
├── OpenAILLM / AsyncOpenAILLM
├── AnthropicLLM / AsyncAnthropicLLM
└── LiteLLM / AsyncLiteLLM
```

### 配置类

```
Union[OpenAIConfig, AnthropicConfig, LiteLLMConfig]
```

### 实例化流程

1. `CoreConfig.from_yaml()` 读取 YAML 配置
2. 根据 `provider` 字段选择对应的 Config 类（OpenAIConfig、AnthropicConfig 或 LiteLLMConfig）
3. `EvolutionEngine.__init__()` 根据 Config 类型实例化对应的 LLM 实例

## 测试

运行以下命令测试不同 provider 的配置加载：

```bash
# 测试配置加载
python test/test_config_loading.py

# 测试 EvolutionEngine LLM 实例化
python test/test_evolution_llm.py
```

## 示例配置文件

项目提供了三个示例配置文件：
- `evolution/test/config_openai_example.yaml` - OpenAI 配置示例
- `evolution/test/config_anthropic_example.yaml` - Anthropic 配置示例
- `evolution/test/config_litellm_example.yaml` - LiteLLM 配置示例

## 扩展新的 Provider

如果需要添加新的 LLM provider：

1. 在 `api/` 目录下创建新的接口文件（如 `interface_newprovider.py`）
2. 创建对应的 Config 类和 LLM 类（继承 `LLMInterface`）
3. 在 `api/__init__.py` 中导出新的类
4. 在 `evolution/config.py` 的 `CoreConfig.llm` 类型中添加新的 Config 类型
5. 在 `CoreConfig.from_yaml()` 方法中添加新 provider 的处理逻辑
6. 在 `evolution/main.py` 的 `EvolutionEngine.__init__()` 中添加新 provider 的实例化逻辑
