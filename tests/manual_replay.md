# 手动回放脚本

适用场景：没时间跑 `test_scenario.py`，或评审希望看到实时 REPL。
严格对应 README §57-65 的 7 步评审流程。

## 前置

```bash
export GEMINI_API_KEY=...
export MEMORY_DB_PATH=/tmp/replay_$(date +%s).db
rm -f "$MEMORY_DB_PATH"
```

## 执行

```bash
python agent.py
```

按下列顺序粘贴输入，观察 stderr 的 `[TOOL]` / `[VERIFY]` 行。

| # | 输入 | 期望现象 |
| --- | --- | --- |
| 1 | `I'm training for a marathon and I hate running in the rain.` | stderr: `[TOOL] save_memory args=...` |
| 2 | `My favorite recovery meal is congee with century egg.` | stderr: `[TOOL] save_memory args=...`（新 id） |
| 3 | 按 `Ctrl+D` 或输入 `exit` | 进程退出 |
| 4 | 再次运行 `python agent.py`（同 `MEMORY_DB_PATH`） | 进入 REPL，记忆依然在 |
| 5 | `What should I do this weekend if it's raining?` | stderr: `[TOOL] search_memory`；回答提到 marathon/rain；若含 `[memory:N]` 必伴随 `[VERIFY] id=N status=ok` |
| 6 | `What's a good meal for after a long run?` | stderr: `[TOOL] search_memory`；回答含 congee / 皮蛋粥；含合法 `[memory:N]` 引用 |
| 7 | `What's my favorite color?` | stderr: `[TOOL] search_memory ... result={"results": []}`；回答含 "don't know"/"不知道"，**不含** `[memory:` |

## 持久化校验

```bash
sqlite3 "$MEMORY_DB_PATH" "SELECT id, content FROM memories;"
```

应至少显示 2 行，分别对应第 1/2 步的陈述。
