检查当前能访问的节点
```bash
$ echo $CRANE_JOB_NODELIST    # on scow-zy
$ echo $SLURM_NODELIST        # on scow 
```

运行：
```
uv run main.py --config evolution/test/trustgame_config_test.yaml --task-config core/trust_game/config.yaml --task-path core/trust_game/ --output-dir output/trust_game
```