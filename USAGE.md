# MindEvolve v2 使用指南

## 快速启动

### 1. 配置环境变量

创建 `.env` 文件，添加必要的环境变量：

```bash
# API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.your-provider.com/v1

# 远程评估服务器（可选，使用分号分隔多个 IP）
HOSTNAME_LIST=192.168.1.100;192.168.1.101;192.168.1.102
```

### 2. 基本运行

使用默认配置运行：

```bash
python main.py
```

### 3. 自定义参数

```bash
python main.py \
  --config evolution/test/config.yaml \
  --task-config core/dictator_game/config.yaml \
  --task-path core/dictator_game \
  --output-dir output
```

## 命令行参数说明

- `--config`: 进化算法配置文件路径（默认: `evolution/test/config.yaml`）
- `--task-config`: 任务配置文件路径（默认: `core/dictator_game/config.yaml`）
- `--task-path`: 任务代码路径（默认: `core/dictator_game`）
- `--output-dir`: 输出目录（默认: `output`）

## 配置文件示例

### 进化算法配置 (`evolution/test/config.yaml`)

```yaml
task_name: "dictator_game"

llm:
  model: "deepseek-v3-250324"
  max_tokens: 16384
  timeout: 6000

evolution_setting:
  max_iterations: 100      # 最大迭代代数
  program_pool_size: 20    # 每代生成的程序数量
```

## 输出结果

程序会在指定的输出目录中生成：

- `program_library_<timestamp>.json`: 每一代的程序库存档
- 包含所有程序的代码、评估指标和元数据

## 恢复训练

如果输出目录中存在历史存档，程序会自动加载最新的存档并继续训练。

## 示例输出

```
============================================================
MindEvolve v2 - 进化算法启动
============================================================

加载进化算法配置: evolution/test/config.yaml
加载任务配置: core/dictator_game/config.yaml
初始化任务插件: dictator_game
初始化进化引擎...

配置信息:
  任务名称: dictator_game
  LLM 模型: deepseek-v3-250324
  最大迭代数: 100
  种群大小: 20
  输出目录: /path/to/output

============================================================
开始进化算法...
============================================================

正在生成初始种群...
评估产生的 20 个程序...
程序 1/20: 成功 (combined_score=0.7523)
程序 2/20: 成功 (combined_score=0.6891)
...
成功评估 18/20 个程序
已保存程序库到: output/program_library_1234567890.json

=== 第 1/100 代 ===
将采样 20 对 parent 和 inspiration 程序...
...
