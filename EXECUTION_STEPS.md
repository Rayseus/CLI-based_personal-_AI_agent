# 执行步骤清单：Personal Memory Agent

> 本文档把 `DEVELOPMENT_PLAN.md` 第 6 节切分为**原子步骤**，每步附：目标 / 产出 / 验收标准 / 测试方案 / 测试用例。
> 全部步骤按顺序执行即可交付。估时合计 ≈ 55 min，保留 5 min buffer。

## 阶段 P0：项目骨架（估时 5 min）

### Step 0.1　创建依赖文件

- **目标**: 声明 Python 依赖
- **产出**: `requirements.txt`
  ```
  google-genai>=0.8.0
  python-dotenv>=1.0.1
  ```
- **验收标准**:
  - 文件存在
  - `pip install -r requirements.txt` 在干净 venv 中成功，无冲突
- **测试方案**: 手动跑一次 `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- **测试用例**:
  - TC-0.1.1：干净环境安装，exit code = 0
  - TC-0.1.2：`python -c "from google import genai; import dotenv"` 无报错

### Step 0.2　创建环境变量样例

- **目标**: 暴露必需配置但不泄漏密钥
- **产出**: `.env.example`
  ```
  GEMINI_API_KEY=your-gemini-api-key
  GEMINI_MODEL=gemini-2.5-flash
  MEMORY_DB_PATH=memory.db
  ```
- **验收标准**:
  - 文件含 3 个 key，均无真实值
  - `.env`（如存在）必须被 `.gitignore` 忽略，但 `.env.example` 不得被忽略
- **测试方案**: `git check-ignore .env.example` → 应返回非 0；`git check-ignore .env` → 应返回 0
- **测试用例**:
  - TC-0.2.1：`.env.example` 在 `git status` 中为可追踪
  - TC-0.2.2：如果创建 `.env` 并写入假 key，`git status` 不显示它

### Step 0.3　创建 `.gitignore`

- **目标**: 忽略临时文件，但**不**忽略 AI 会话记录
- **产出**: `.gitignore`
  ```
  .venv/
  __pycache__/
  *.pyc
  .env
  memory.db
  .DS_Store
  ```
- **验收标准**:
  - 不含 `.cursor/` `.claude/` `ai-session/` `*.jsonl`
  - `git check-ignore ai-session/agent-transcripts/*.jsonl` 返回非 0
- **测试方案**: `grep -E '^(\.cursor|\.claude|ai-session|\*\.jsonl)' .gitignore` → 应无输出
- **测试用例**:
  - TC-0.3.1：`git status` 仍能看到 `ai-session/` 下变化

### Step 0.4　创建空模块骨架

- **目标**: 让后续各 step 可 import
- **产出**:
  ```
  agent.py           # def main(): pass
  memory_store.py    # class MemoryStore: pass
  tools.py           # TOOL_SCHEMAS = []; def dispatch(...): ...
  tests/__init__.py
  tests/test_scenario.py   # 占位
  ```
- **验收标准**: `python -c "import agent, memory_store, tools"` exit 0
- **测试方案**: 直接 import 校验
- **测试用例**:
  - TC-0.4.1：三个模块 import 无 SyntaxError / ImportError

---

## 阶段 P1：持久化层 MemoryStore（估时 15 min）

### Step 1.1　建表与连接

- **目标**: SQLite 打开/建表幂等
- **产出**: `MemoryStore.__init__(db_path)` + `_init_schema()`
- **Schema**:
  ```sql
  CREATE TABLE IF NOT EXISTS memories (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      content    TEXT NOT NULL,
      tags       TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL
  );
  ```
- **验收标准**:
  - 首次实例化时创建 `memory.db` 文件
  - 二次实例化不抛错、不清空已有数据
  - `tags` 列以 JSON 字符串存储
- **测试用例**:
  - TC-1.1.1：临时目录实例化 → `sqlite3 ... ".tables"` 输出 `memories`
  - TC-1.1.2：重复实例化 10 次 → 数据不丢

### Step 1.2　`save(content, tags) -> int`

- **目标**: 写入一条记忆并返回自增 id
- **验收标准**:
  - 参数：`content: str`（非空，trim 后 ≥ 1 字符）、`tags: list[str]`
  - 返回值：新行的 `id`（整数 ≥ 1）
  - `created_at` 为 ISO8601 UTC 字符串
  - 空 content 抛 `ValueError`
- **测试用例**:
  - TC-1.2.1：`save("hello", ["greet"])` 返回 1；`save("world", [])` 返回 2
  - TC-1.2.2：`save("")` 抛 `ValueError`
  - TC-1.2.3：查询原始行 `tags` 字段解析为 `["greet"]`

### Step 1.3　`search(query, top_k=3) -> list[dict]`

- **目标**: 基于关键词 + tags 交集的评分检索
- **打分算法**（时间紧的降级版，不用 embedding）:
  ```
  score = token_overlap(query, content) * 1.0
        + tag_overlap(query_tokens, tags) * 2.0
  ```
  过滤 `score > 0`，按降序取 top_k
- **验收标准**:
  - 返回结构：`[{"id": int, "content": str, "tags": list[str], "score": float}]`
  - 空库或全 0 分 → 返回 `[]`
  - 结果按 `score` 降序
- **测试用例**:
  - TC-1.3.1：空库 `search("anything")` → `[]`
  - TC-1.3.2：存入 "I'm training for a marathon" + tags `["running"]`，查询 "marathon" → 命中
  - TC-1.3.3：查询 "favorite color" → `[]`（防幻觉关键）
  - TC-1.3.4：存两条不同相关度的记忆，查询后高分在前

### Step 1.4　`exists(memory_id) -> bool`

- **目标**: 确定性校验引用 id 是否真实存在
- **验收标准**:
  - 存在返回 `True`，否则 `False`
  - 非 int 输入返回 `False`（不抛错）
- **测试用例**:
  - TC-1.4.1：`save(...)` 得到 id=5 → `exists(5) is True`
  - TC-1.4.2：`exists(999)` → `False`
  - TC-1.4.3：`exists("abc")` → `False`

### Step 1.5　MemoryStore 单元测试

- **产出**: `tests/test_memory_store.py`
- **验收标准**: 覆盖 Step 1.1–1.4 全部 TC，`python -m unittest tests/test_memory_store.py` 全绿
- **测试方案**: 每个用例使用 `tempfile.NamedTemporaryFile(suffix=".db")` 隔离

---

## 阶段 P2：工具层 tools.py（估时 15 min）

### Step 2.1　工具 Schema 定义

- **目标**: LLM-agnostic 的 JSON schema（保留 OpenAI 风格 `{"type":"function","function":{...}}` 外壳以便跨 SDK 复用），由 `agent.py` 转换为 Gemini 原生 `types.FunctionDeclaration`
- **产出**: `TOOL_SCHEMAS = [save_memory_schema, search_memory_schema]`
- **`save_memory` schema**:
  ```python
  {
    "type": "function",
    "function": {
      "name": "save_memory",
      "description": "Store a fact the user told about themselves. Call this IMMEDIATELY when the user states a preference, goal, habit, or personal fact.",
      "parameters": {
        "type": "object",
        "properties": {
          "content": {"type": "string", "description": "The full statement from the user, rewritten in first person."},
          "tags": {"type": "array", "items": {"type": "string"}, "description": "2-5 topical keywords, lowercase."}
        },
        "required": ["content", "tags"]
      }
    }
  }
  ```
- **`search_memory` schema**:
  ```python
  {
    "type": "function",
    "function": {
      "name": "search_memory",
      "description": "Retrieve relevant stored memories before answering any question that may depend on user preferences. MUST be called before personalized answers.",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "top_k": {"type": "integer", "default": 3}
        },
        "required": ["query"]
      }
    }
  }
  ```
- **验收标准**: `json.dumps(TOOL_SCHEMAS)` 可序列化；字段名与 OpenAI API 规范一致
- **测试用例**:
  - TC-2.1.1：`len(TOOL_SCHEMAS) == 2`
  - TC-2.1.2：`TOOL_SCHEMAS[0]["function"]["name"] == "save_memory"`

### Step 2.2　Dispatcher

- **目标**: 根据 LLM 返回的 tool_call 名称路由到 MemoryStore 方法
- **产出**: `def dispatch(tool_name: str, arguments: dict, store: MemoryStore) -> dict`
- **验收标准**:
  - `save_memory` → `{"id": <int>, "status": "saved"}`
  - `search_memory` → `{"results": [...]}`（空时也返回 `{"results": []}`）
  - 未知工具 → `{"error": "unknown tool: <name>"}`
  - 参数缺失 → `{"error": "missing field: <name>"}`，不抛异常
- **测试用例**:
  - TC-2.2.1：正确 save 参数 → `{"id": 1, "status": "saved"}`
  - TC-2.2.2：search 空库 → `{"results": []}`
  - TC-2.2.3：`dispatch("foo", {}, store)` → 含 `error` key
  - TC-2.2.4：`dispatch("save_memory", {"tags": []}, store)` → `error` 含 `content`

### Step 2.3　引用校验器 `verify_citations`

- **目标**: 确定性剥离不存在的 `[memory:<id>]` 引用
- **产出**:
  ```python
  def verify_citations(reply: str, store: MemoryStore) -> tuple[str, list[dict]]:
      """Returns (cleaned_reply, verification_log)."""
  ```
- **规则**:
  - 匹配正则 `\[memory:(\d+)\]`
  - 对每个 id 调 `store.exists(id)`
  - 失败的引用从文本中删除，并在 log 中记录 `{"id": n, "status": "fail"}`
  - 返回 cleaned_reply 与 log 列表
- **验收标准**:
  - 无引用的回复原样返回，log 为 `[]`
  - 所有引用都真实 → 文本不变，log 全部 `ok`
  - 混合场景 → 只剥离虚假引用
- **测试用例**:
  - TC-2.3.1：输入 `"Try congee [memory:2]"`，store 含 id=2 → cleaned 不变
  - TC-2.3.2：输入 `"Try X [memory:99]"`，99 不存在 → cleaned 去掉 `[memory:99]`，log 含 `fail`
  - TC-2.3.3：输入 `"Hello"` → cleaned=`"Hello"`，log=`[]`
  - TC-2.3.4：输入 `"A [memory:1] B [memory:99] C"` + 仅 1 存在 → 输出保留 `[memory:1]`，去除 `[memory:99]`

### Step 2.4　工具层单元测试

- **产出**: `tests/test_tools.py`
- **验收标准**: Step 2.1–2.3 所有 TC 全绿

---

## 阶段 P3：Agent CLI 主循环（估时 15 min）

### Step 3.1　配置加载与 Gemini 客户端

- **目标**: 启动时读取 `.env`，校验 API key
- **产出**: `agent.py` 中 `load_config()` 返回 `(api_key, model, db_path)`；`main()` 里 `genai.Client(api_key=...)`
- **验收标准**:
  - `GEMINI_API_KEY` 缺失 → 打印错误并 `sys.exit(1)`
  - 成功时正常进入 REPL
- **测试用例**:
  - TC-3.1.1：清空 env 启动 → exit code = 1 且 stderr 含 `GEMINI_API_KEY`
  - TC-3.1.2：设置假 key 启动至少能进入 REPL 提示符

### Step 3.2　System Prompt 常量

- **目标**: 硬约束 LLM 行为
- **产出**: `agent.py::SYSTEM_PROMPT` 字符串，包含以下子句：
  1. 用户陈述个人事实 → **必须** 先 `save_memory`
  2. 用户提问涉及偏好/历史 → **必须** 先 `search_memory`
  3. 引用记忆必须使用 `[memory:<id>]`，且 id 来自 `search_memory` 返回
  4. `search_memory` 返回空时 → 必须回答 "I don't know — you haven't told me that." 不得猜测
  5. 不得把记忆内容当成外部事实引用（只说 "you told me..."）
- **验收标准**: 5 条规则在 prompt 中可 grep 到
- **测试用例**:
  - TC-3.2.1：`all(keyword in SYSTEM_PROMPT for keyword in ["save_memory", "search_memory", "[memory:", "I don't know"])`

### Step 3.3　Tool-use 循环（Gemini）

- **目标**: 处理 Gemini 的多轮 function_call
- **产出**: `def chat(user_msg, history, store, client, model) -> str`
- **流程**:
  ```
  1. history.append(Content(role="user", parts=[Part.from_text(...)]))
  2. loop (最多 TOOL_LOOP_LIMIT 次):
       resp = client.models.generate_content(
           model=model, contents=history,
           config=GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                        tools=[...], temperature=0.2))
       content = resp.candidates[0].content
       history.append(content)
       fn_calls = [p.function_call for p in content.parts if p.function_call]
       if not fn_calls:
           text = concat(p.text for p in content.parts)
           cleaned, vlog = verify_citations(text, store)
           log vlog; 如果 cleaned != text 则覆写 history[-1]
           return cleaned
       for fc in fn_calls:
           result = dispatch(fc.name, dict(fc.args), store)
           log [TOOL]
           response_parts.append(Part.from_function_response(name=fc.name, response=result))
       history.append(Content(role="user", parts=response_parts))
  3. 超限抛 RuntimeError("tool loop exceeded")
  ```
- **验收标准**:
  - 循环最多 `TOOL_LOOP_LIMIT`（=6）轮，超过抛错
  - 每次 tool 调用在 stderr 打印 `[TOOL] save_memory args=... result=...`
  - 每次验证在 stderr 打印 `[VERIFY] id=2 status=ok`
- **测试用例**（mock Gemini client，仅替换 `client.models.generate_content`）:
  - TC-3.3.1：mock 返回 1 次 `save_memory` function_call → DB 插入 1 行
  - TC-3.3.2：mock 返回 `search_memory` → tool result 传回后继续对话
  - TC-3.3.3：mock 连续 >TOOL_LOOP_LIMIT 轮 function_call → 抛 `RuntimeError("tool loop exceeded")`

### Step 3.4　REPL

- **目标**: 命令行交互入口
- **产出**: `agent.py::main()`
- **验收标准**:
  - 启动打印 `Personal Agent ready. Type 'exit' to quit.`
  - 提示符 `you> ` / `agent> `
  - `exit` / `quit` / Ctrl+D 干净退出（flush DB、关连接）
  - 空输入跳过，不发 API 请求
- **测试用例**:
  - TC-3.4.1：输入 `exit` → 退出码 0
  - TC-3.4.2：输入空行 → 无 API 调用（通过 mock 断言）

---

## 阶段 P4：端到端评审场景测试（估时 5 min）

### Step 4.1　场景测试脚本

- **产出**: `tests/test_scenario.py`
- **测试策略**: **不** mock LLM，但**隔离 DB**（`tempfile`）并使用真实 `GEMINI_API_KEY`；CI 环境无 key 时 skip。
- **测试流程**（严格对应 README 第 57-65 行）:

  | 步骤 | 输入 | 断言 |
  | --- | --- | --- |
  | S1 | 启动（临时 db） | DB 文件存在且 `SELECT COUNT(*) FROM memories` = 0 |
  | S2 | 发 "我正在备战马拉松，我讨厌雨天跑步" | DB 行数 = 1；tool log 含 `save_memory` |
  | S3 | 发 "我最爱的恢复餐是皮蛋粥" | DB 行数 = 2 |
  | S4 | 关闭 store 重新打开（模拟重启） | `SELECT COUNT(*)` 仍 = 2 |
  | S5 | 问 "这周末下雨做什么？" | 响应含 `marathon` 或 `running` 相关建议；tool log 含 `search_memory`；VERIFY 至少 1 条 ok |
  | S6 | 问 "长跑后吃什么？" | 响应含 `congee` 或 `皮蛋粥`；含合法 `[memory:\d+]` 引用 |
  | S7 | 问 "我最喜欢的颜色是什么？" | 响应含 "don't know" / "不知道"；tool log 含 `search_memory` 且 result `results=[]`；响应**不**含 `[memory:` |

- **验收标准**: 7 条断言全部通过
- **测试方案**:
  - 使用 `capsys` 或自定义 logger 捕获 `[TOOL]` / `[VERIFY]` 行
  - `MEMORY_DB_PATH` 通过环境变量传入临时文件

### Step 4.2　手动回放脚本（降级方案）

- **产出**: `tests/manual_replay.md`，列出 7 步人工命令
- **触发条件**: 时间不足以写完 4.1 时使用
- **验收标准**: 按文档跑一遍命令，肉眼对齐 7 条断言

---

## 阶段 P5：文档与交付（估时 5 min）

### Step 5.1　追加 README 架构章节

- **目标**: 向评审解释"为什么这么设计"
- **产出**: `README.md` 末尾新增 3 节
  - `## Architecture` — 文件职责、控制流图
  - `## Tool Schema Design` — 为何 save/search 分离、tags 由 LLM 抽取的理由
  - `## Verification` — 正则匹配 + `exists()` 的确定性校验流程，附日志样例
  - `## Setup & Run` — 一条安装、一条运行
- **验收标准**:
  - 4 个新标题 grep 可见
  - `Setup & Run` 含 `pip install -r requirements.txt` 和 `python agent.py` 两条命令

### Step 5.2　AI 会话同步 + 最终提交

- **目标**: 不丢失任何对话记录
- **流程**:
  ```
  bash scripts/sync-ai-session.sh
  git add -A
  git commit -m "feat: implement personal memory agent"
  git push origin main
  ```
- **验收标准**:
  - `git status` 输出 `nothing to commit, working tree clean`
  - GitHub 远端最新 commit hash 与本地 `git rev-parse HEAD` 一致
  - 远端 `ai-session/agent-transcripts/` 下 jsonl 存在

---

## 全局冒烟测试（push 前必跑）

```bash
# 1. 模块可 import
python -c "import agent, memory_store, tools"

# 2. 单测全绿
python -m unittest discover tests -v

# 3. 一键冷启动评审场景（需要 GEMINI_API_KEY）
export MEMORY_DB_PATH=/tmp/smoke_$(date +%s).db
python tests/test_scenario.py

# 4. 验证持久化
sqlite3 "$MEMORY_DB_PATH" "SELECT COUNT(*) FROM memories;"   # 期望 2
```

全 4 步通过 → 可以 push。
