# 开发计划：Personal Memory Agent

> 基于 `README.md` 的挑战要求，在 60 分钟限时内交付一个可运行、可验证、无幻觉引用的 CLI Personal Agent。

## 1. 核心目标拆解

| 能力 | 必须满足 | 验收方式 |
| --- | --- | --- |
| 学习（Save） | LLM 通过 `save_memory` 工具调用写入持久化存储 | SQLite 文件存在对应条目 |
| 回忆（Recall） | LLM 通过 `search_memory` 工具检索相关记忆 | 响应中含记忆 ID + 内容引用 |
| 验证（Verify） | 回答前对引用的 memory_id 做确定性存在性校验 | 日志打印 `VERIFY: id=... ok/fail` |
| 持久化 | 杀进程后重启记忆仍在 | 重启后 `search_memory` 可查到 |
| 拒答 | 无匹配记忆时明确 "I don't know" | 日志显示空结果 + 回答不含编造事实 |

## 2. 技术选型

- **语言**: Python 3.10+（README 推荐，生态最快）
- **LLM**: Google Gemini（`gemini-2.5-flash`，tool use 成熟且免费额度足够评审），通过环境变量 `GEMINI_API_KEY` 注入
- **SDK**: `google-genai`（新版统一 SDK）
- **持久化**: SQLite（`stdlib` 自带，零依赖）
- **检索**: 关键词 + tags 交集打分（确定性，零额外依赖）
- **依赖**: `google-genai`、`python-dotenv`
- **入口**: `python agent.py`，一键安装 `pip install -r requirements.txt`

## 3. 架构设计

```
┌─────────────────┐
│   CLI 主循环     │  agent.py
└────────┬────────┘
         │ user input
         ▼
┌─────────────────┐     tool_call     ┌──────────────────┐
│   LLM Client    │ ─────────────────▶│  Tool Dispatcher │
│ (OpenAI w/ tools)│◀──── tool_result ─│  save/search     │
└─────────────────┘                    └────────┬─────────┘
                                                │
                                    ┌───────────┼───────────┐
                                    ▼           ▼           ▼
                               save_memory  search_memory  verify_memory
                                    │           │           │
                                    └─────┬─────┴─────┬─────┘
                                          ▼           ▼
                                    ┌──────────────────┐
                                    │  MemoryStore     │
                                    │  (SQLite)        │
                                    └──────────────────┘
```

### 3.1 文件结构

```
CLI-base-Agent/
├── agent.py              # CLI 主循环 + LLM 调度
├── memory_store.py       # SQLite 封装（CRUD + 检索）
├── tools.py              # 工具 schema + dispatcher + verify
├── requirements.txt
├── README.md             # 已存在，追加架构说明章节
└── tests/
    └── test_scenario.py  # 还原评审场景
```

### 3.2 数据模型

```sql
CREATE TABLE memories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    content    TEXT NOT NULL,
    tags       TEXT,              -- JSON 数组，用于过滤
    created_at TEXT NOT NULL
);
```

## 4. 工具 Schema 设计（关键决策）

### 4.1 `save_memory`

- **触发条件**: 用户陈述自身事实/偏好/目标/习惯
- **参数**: `content: str`（完整陈述）、`tags: list[str]`（主题关键词，如 `["running", "weather"]`）
- **返回**: `{"id": 12, "status": "saved"}`
- **设计理由**: 让 LLM 自己抽取 tags 比服务端做 NLP 更可靠，同时便于后续过滤检索。

### 4.2 `search_memory`

- **触发条件**: 用户提问需要个性化上下文
- **参数**: `query: str`、`top_k: int = 3`
- **返回**: `[{"id": 12, "content": "...", "score": 0.82}, ...]`（空列表即表示未知）
- **设计理由**: 强制 LLM 先检索再回答，返回空时必须承认未知，这是防幻觉的硬边界。

### 4.3 验证机制（不暴露为 LLM 工具，属内部中间件）

- 解析 LLM 最终回复中的 `[memory:<id>]` 引用标记
- 对每个 id 调用 `memory_store.exists(id)`
- 若存在不合法 id → 剥离该引用并在控制台打印 `VERIFY FAIL`
- 若回复声称"根据记忆"却无任何引用 → 退化为中性回复
- **设计理由**: 把验证做成确定性后处理，而非 prompt 约束，保证不可被 LLM 绕过

## 5. Prompt 策略

System prompt 关键条款：

1. "如果用户陈述个人事实，**必须**先调用 `save_memory`"
2. "如果用户提问涉及个人偏好，**必须**先调用 `search_memory`"
3. "回答中引用记忆时必须使用 `[memory:<id>]` 格式，且 id 必须来自 `search_memory` 的返回"
4. "`search_memory` 返回空时，直接回答 'I don't know — you haven't told me that.'，不得猜测"

## 6. 实施步骤（60 分钟切片）

| 时段 | 任务 | 产出 |
| --- | --- | --- |
| 0-5 min | 初始化项目结构、`requirements.txt`、`.env.example` | 骨架可 import |
| 5-20 min | `memory_store.py`: SQLite 初始化、`save/search/exists` | 单独 `python -c` 可跑通 |
| 20-35 min | `tools.py`: schema 定义 + dispatcher + 验证后处理 | 单元函数可调 |
| 35-50 min | `agent.py`: Gemini tool-use 循环、CLI REPL、日志 | 端到端跑通评审场景 |
| 50-55 min | `tests/test_scenario.py`: 复现 README 评审 7 步 | 绿灯 |
| 55-60 min | 补完 `README.md` 架构章节、commit & push | 交付 |

## 7. 评估场景自测清单

严格对应 README 第 57-65 行：

- [ ] 全新启动 → DB 文件不存在时自动建表
- [ ] 输入马拉松/雨天陈述 → 日志显示 `save_memory` 调用且 DB 行数 +1
- [ ] 输入皮蛋粥陈述 → DB 行数 +1
- [ ] `Ctrl+C` 杀进程 → 重启后 `sqlite3 memory.db "SELECT COUNT(*)"` 返回 2
- [ ] 问"下雨周末做什么" → 响应含 `[memory:1]` 且 VERIFY ok
- [ ] 问"长跑后吃什么" → 响应含 `[memory:2]` 且推荐皮蛋粥
- [ ] 问"最喜欢的颜色" → 日志 `search_memory -> []`，响应为 "I don't know"

## 8. 风险与降级方案

| 风险 | 降级方案 |
| --- | --- |
| Gemini 限流 / 超时 | 捕获异常、打印 `[ERROR]`、保留历史等用户重试 |
| Tool call 参数解析失败 | `dispatch` 返回 `{"error":...}`，LLM 可看到并自行修正 |
| `GEMINI_API_KEY` 缺失 | 启动时提示并 exit 1，不静默失败 |
| 时间不够写测试 | 保留手动 REPL 回放脚本 `tests/manual_replay.md` |

## 9. 提交规范

- 每完成一个切片即 commit，遵循约定式提交
- 示例：`feat(store): add sqlite memory persistence`、`feat(agent): wire openai tool-use loop`、`test: cover evaluator scenario`
- **不得** 将 `.cursor/`、`.claude/`、`ai-session/` 加入 `.gitignore`
- **每次 commit 前**运行 `bash scripts/sync-ai-session.sh`，将 Cursor 全局会话记录同步到仓库内 `ai-session/`，然后 `git add ai-session/`
- 最后一次 push 前运行 `python tests/test_scenario.py` 确保绿灯

## 10. README 补充章节（交付前写入）

需在现有 `README.md` 末尾新增：

- `## Architecture` — 工具 schema 的设计理由
- `## Verification` — 确定性校验流程 + 日志样例
- `## Setup & Run` — `pip install -r requirements.txt` + `export OPENAI_API_KEY=...` + `python agent.py`
