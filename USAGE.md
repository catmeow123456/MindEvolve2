# MindEvolve v2 使用指南

## 快速启动
以 dictator game 的计算建模任务为例, 运行本框架

### 1. 准备环境
提示：框架支持分布式运行来提高性能，此时需要通过鹤思或Slurm调度器来在超算环境中运行。

配置免密登录
```bash
mkdir -p ~/.ssh

# 如果服务器没有生成过密钥, 需要生成
ssh-keygen

# 配置免密
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

创建 `.env` 文件，添加必要的环境变量：
```bash
cp .env.template .env
vi .env
```

安装依赖
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 编写任务的配置、提示词与评估代码
框架提供了dictator game的所有配置、提示词与评估代码，位于 core/dictator_game , 如需执行其他任务，请复制 core/dictator_game 目录并自行修改。

### 3. 自定义参数
由于框架迭代运行时间长，建议在 tmux 中运行，避免程序运行中断
```bash
uv run main.py \
  --config evolution/test/trustgame_config_test.yaml \
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
