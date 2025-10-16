# Claude Agent 使用指南

## 概述

`ClaudeAgent` 是一个基于 Claude Code SDK 的代码生成工具，它能够在独立的工作目录中执行复杂的代码生成任务。

## 主要特性

- **独立工作目录**：每个任务在 `{agent_dir}/{timestamp}_{task_uid}/` 中执行
- **自动文件管理**：自动创建和管理工作目录
- **重试机制**：支持配置重试次数，提高任务成功率
- **明确的文件输出**：在 prompt 中自动指定目标文件
- **完整集成**：与现有的 evolution engine 无缝集成

## 配置示例

### YAML 配置文件

```yaml
task_name: "my_task"
output_dir: "output"

llm:
  provider: "claude_code"
  model: "claude-sonnet-4-20250514"
  system_prompt: "You are an expert Python programmer."
  permission_mode: "acceptEdits"
  max_turns: 15
  allowed_tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
  agent_dir: ".claude_code"
  retries: 3
```

### Python 代码

```python
from evolution import ClaudeAgent, ClaudeCodeConfig

# 创建配置
config = ClaudeCodeConfig(
    model="claude-sonnet-4-20250514",
    system_prompt="You are an expert Python programmer.",
    permission_mode="acceptEdits",
    max_turns=10,
    allowed_tools=["Read", "Write", "Edit", "Bash"],
    agent_dir=".claude_code",
    retries=3
)

# 创建 agent
agent = ClaudeAgent(config)

# 执行任务
result = await agent.run(
    prompt="Create a Python function that calculates factorial.",
    task_uid="factorial_001",
    target_file="program.py"
)

print(result)  # 输出生成的代码
```

## 配置参数说明

### ClaudeCodeConfig

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | str | "claude-sonnet-4-20250514" | Claude 模型名称 |
| `system_prompt` | str | "You are a helpful coding assistant." | 系统提示词 |
| `permission_mode` | str | "acceptEdits" | 权限模式（default, acceptEdits, plan, bypassPermissions） |
| `max_turns` | int | 10 | 最大对话轮数 |
| `allowed_tools` | list[str] | ["Read", "Write", "Edit", "Bash", "Glob", "Grep"] | 允许的工具列表 |
| `agent_dir` | str | ".claude_code" | Agent 工作目录的根目录 |
| `retries` | int | 3 | 任务失败时的重试次数 |

### ClaudeAgent.run() 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `prompt` | str | - | 任务提示词（必需） |
| `task_uid` | str | - | 任务唯一标识符（必需） |
| `target_file` | str | "program.py" | 目标文件名（相对于工作目录） |

## 工作原理

1. **创建工作目录**：根据时间戳和 task_uid 创建唯一的工作目录
2. **构建完整 Prompt**：在用户 prompt 后自动添加输出文件指示
3. **执行任务**：使用 Claude Code SDK 在工作目录中执行任务
4. **读取结果**：任务完成后读取指定的目标文件
5. **重试机制**：如果任务失败，自动重试指定次数

## 与 Evolution Engine 集成

在 `evolution/main.py` 中，`EvolutionEngine` 会自动识别 `ClaudeCodeConfig` 并创建 `ClaudeAgent`：

```python
# 配置会自动识别
core_config = CoreConfig.from_yaml("config.yaml")
engine = EvolutionEngine(task_plugin, core_config)

# gen_program 会自动使用正确的方法
program_code = await engine.gen_program(prompt)
```

## 注意事项

1. **Claude Code CLI 必须已安装**：确保系统中已正确安装和配置 Claude Code CLI
2. **工作目录**：每个任务都在独立目录中执行，目录名称为 `{timestamp}_{task_uid}`
3. **目标文件**：Prompt 中会自动添加目标文件指示，确保 Claude 知道将代码写入哪个文件
4. **重试**：如果任务失败，会自动重试，但每次重试都使用同一个工作目录

## 示例

参考以下文件获取更多使用示例：
- `test/test_claude_agent.py` - 单元测试
- `test/example_claude_agent_usage.py` - 完整使用示例
- `evolution/test/config_claude_code_example.yaml` - 配置文件示例
