# CLI-base-Agent: Multi-Tool CLI Agent with Persistent Memory & Verification

## Challenge / 编程挑战

Build a working CLI-based personal AI agent that remembers facts about the user across sessions and uses tool calls to answer questions grounded in that memory. This is the core loop of a personal AI agent.

## What You're Building

A command-line agent that a user can chat with. The agent can:
1. **Learn** — when the user tells it something about themselves (preferences, goals, habits, facts), the agent stores it in a local persistent memory store.
2. **Recall** — when the user asks a question, the agent retrieves relevant memories and uses them to give a personalized, grounded answer.
3. **Verify** — before returning any answer that references a stored memory, the agent runs a deterministic check to confirm the cited memory actually exists in the store (no hallucinated citations).

The agent must be driven by an LLM (GPT-4o, Claude 3.5, Gemini, or any frontier model) with explicit tool use — not prompt stuffing. The memory store must persist across process restarts (i.e., kill the CLI and restart it — memories must still be there).

## Scenario to Support (Used in Evaluation)

The evaluator will run through this exact sequence:
1. Start the agent fresh (empty memory).
2. Tell it: *"I'm training for a marathon and I hate running in the rain."*
3. Tell it: *"My favorite recovery meal is congee with century egg."*
4. Kill the process and restart.
5. Ask: *"What should I do this weekend if it's raining?"* — expect a personalized suggestion that references the marathon training and rain aversion.
6. Ask: *"What's a good meal for after a long run?"* — expect congee to be recommended with a memory citation.
7. Ask: *"What's my favorite color?"* — the agent must say it doesn't know (no hallucination), and this must be backed by a failed memory lookup (verifiable in logs or output).

## Scope Constraints

- CLI only — no web UI required.
- Local file or SQLite for memory persistence — no external database required.
- One command to install and one command to run (`npm install && npm start` or `pip install -r requirements.txt && python agent.py`, etc.).
- A `README.md` that explains architecture decisions: why you structured tools the way you did, and how verification prevents hallucination.

## What Matters (Design Judgment, Not Code Volume)

The interesting decisions you must make:
- How do you design the tool schema so the LLM reliably calls `save_memory` vs `search_memory` at the right time?
- How do you structure memory entries so retrieval is accurate (not just keyword match)?
- How do you implement the verification step that confirms cited memories are real before the agent responds?
- How do you handle the "I don't know" case cleanly — making the LLM admit ignorance rather than confabulate?

These are agent architecture decisions AI tools can't make for you — you direct them.

---

构建一个可在命令行运行的个人 AI Agent，它能够跨会话记住用户信息，并通过工具调用来回答基于记忆的问题。这是 Personal Agent 的核心循环。

## 你要构建什么

一个用户可以与之对话的命令行 Agent，它能够：
1. **学习** —— 当用户告知个人信息（偏好、目标、习惯、事实）时，Agent 将其存入本地持久化记忆库。
2. **回忆** —— 当用户提问时，Agent 检索相关记忆并给出个性化、有据可查的回答。
3. **验证** —— 在任何引用了存储记忆的回答输出之前，Agent 必须运行确定性检查，确认所引用的记忆确实存在于存储中（不允许幻觉引用）。

Agent 必须通过显式工具调用驱动（GPT-4o、Claude 3.5、Gemini 等任意前沿模型均可），不得将记忆全部塞入 prompt。记忆库必须在进程重启后依然存在（杀掉 CLI 再重启，记忆必须还在）。

## 评估场景（评审将逐步执行以下流程）

1. 全新启动 Agent（空记忆库）。
2. 告诉它：*"我正在备战马拉松，我很讨厌在雨天跑步。"*
3. 告诉它：*"我最喜欢的恢复餐是皮蛋粥。"*
4. 杀掉进程并重启。
5. 问：*"这个周末如果在下雨，我应该做什么？"* —— 期望得到结合马拉松训练和雨天厌恶的个性化建议。
6. 问：*"长跑后吃什么好？"* —— 期望 Agent 推荐皮蛋粥并给出记忆引用。
7. 问：*"我最喜欢的颜色是什么？"* —— Agent 必须明确表示不知道（不得幻觉），且此判断必须基于一次失败的记忆检索（可在日志或输出中验证）。

## 范围约束

- 仅命令行，无需 Web UI。
- 本地文件或 SQLite 持久化，无需外部数据库。
- 一条命令安装，一条命令运行（如 `npm install && npm start` 或 `pip install -r requirements.txt && python agent.py`）。
- `README.md` 中需说明架构决策：为何如此设计工具 schema，以及验证步骤如何防止幻觉。

## 关键考察点（设计判断，而非代码量）

你必须做出的关键设计决策：
- 如何设计工具 schema，使 LLM 在正确时机可靠地调用 `save_memory` 与 `search_memory`？
- 如何组织记忆条目，使检索准确（不只是关键词匹配）？
- 如何实现验证步骤，确保在 Agent 回答前所引用的记忆真实存在？
- 如何干净地处理"我不知道"的情况——让 LLM 承认无知而非捏造答案？

这些是 Agent 架构决策，AI 工具无法替你做出——你需要主导方向。

## Requirements / 需求

- The agent must persist memory across process restarts using a local file or SQLite store — kill and restart the CLI, all previously saved memories must still be accessible.
- The agent must use explicit LLM tool calls (function calling / tool use API) for at least two distinct tools: one for saving memories and one for searching/retrieving them — no prompt stuffing of the full memory store.
- Before returning any response that cites a stored memory, the agent must run a deterministic verification step that confirms the cited memory ID or content exists in the store. If verification fails, the agent must not return that citation. This behavior must be visible in logs or terminal output.
- When asked about something the user never told it (e.g., favorite color), the agent must explicitly respond that it does not know — backed by a failed or empty memory search result — with no hallucinated facts.
- One-command setup and one-command run (e.g., pip install -r requirements.txt && python agent.py). A README.md must explain the tool schema design and how the verification step works.

## Evaluation Criteria / 评判标准

- Architecture quality: Are the tool schemas well-designed? Does the tool split (save vs. search vs. verify) make the LLM reliably take the right action at the right time, or does it leak / hallucinate?
- Verification correctness: Does the deterministic verification step actually prevent hallucinated memory citations? Evaluator will inspect the code path, not just trust the output.
- Persistence reliability: Does memory survive a process kill and cold restart? Evaluator will test this directly with the stated scenario.
- Hallucination resistance: Does the agent cleanly say 'I don't know' for unknown facts, and is this grounded in a real failed lookup — not just a prompt instruction?
- README clarity: Does the candidate articulate *why* they made specific design choices (tool schema shape, memory structure, verification approach)? This reveals whether they directed the AI tools or just accepted generated output.
- Code quality under time pressure: Is the code runnable, readable, and free of obvious bugs? Does error handling exist for LLM tool call failures?

## Tech Hints / 技术提示

- Python (recommended) or TypeScript/Node.js
- OpenAI API / Anthropic API / Google Gemini API — any frontier model with tool use support
- SQLite (via sqlite3 or better-sqlite3) or JSON file for persistence
- Optional: sentence-transformers or OpenAI embeddings for semantic memory search (bonus, not required)
- Optional: LangChain, LlamaIndex, or raw API calls — candidate's choice reveals judgment

## Rules / 规则

- **Time limit / 时间限制**: 60 minutes (2026-04-21 13:43 UTC)
- **AI tools required / 必须使用 AI 工具**: Claude Code, Cursor, Copilot, etc. This challenge is designed to be impossible without AI tools — use them.
- **AI session logs are MANDATORY / AI 会话记录为必交项**: Your AI interaction history (`.claude/`, `.cursor/`, `.codex/`, `.windsurf/`, or `ai-session/`) is a core evaluation deliverable. Do NOT delete or `.gitignore` these directories. **Submissions without AI session logs will receive a significant scoring penalty.** / 不提交 AI 会话记录将严重扣分。
- **Multiple pushes OK / 可以多次 push**: We evaluate your last push before the deadline
- **Language / 语言**: Any programming language, any framework

## Getting Started / 开始

1. Read this README carefully
2. Use Claude Code or your preferred AI tool
3. Build a complete, runnable project
4. `git push` your code (multiple pushes OK)
5. Keep the `.claude/` directory for AI collaboration evaluation

Good luck! / 祝你好运！

---

# Implementation / 实现

## Setup & Run

```bash
# 1. install (Python 3.10+)
pip install -r requirements.txt

# 2. configure
cp .env.example .env
# edit .env and set GEMINI_API_KEY

# 3. run the CLI
python agent.py

# 4. run the test suite (unit tests always; scenario test needs GEMINI_API_KEY)
python -m unittest discover tests -v
```

Environment variables (see `.env.example`):

| Var | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | yes | — | Google AI Studio key |
| `GEMINI_MODEL` | no | `gemini-2.5-flash` | Model name passed to `client.models.generate_content` |
| `MEMORY_DB_PATH` | no | `memory.db` | SQLite file path |
| `AGENT_LOG_PATH` | no | `agent.log` | Where `[TOOL]` and `[VERIFY]` diagnostics are written. CLI stays clean by default. |
| `AGENT_DEBUG` | no | `0` | Set to `1` to also tee diagnostics to the terminal while you chat. |

Keeping the CLI clean: by default the REPL only shows `you>` /
`agent>` lines. The deterministic verifier and tool-call trace are
still fully auditable — they are appended to `agent.log`, which is
also where the "I don't know" / `"results": []` evidence required
by the challenge lives. Use `tail -f agent.log` in another terminal
or set `AGENT_DEBUG=1` to see them inline.

## Architecture

```
┌────────────────┐   user text    ┌─────────────────────┐
│   CLI REPL     │ ─────────────▶ │      agent.chat     │
│  (agent.main)  │ ◀────────────  │  Gemini tool-loop   │
└────────────────┘   reply        └──────────┬──────────┘
                                             │
                                  tool_call  │  tool_response
                                             ▼
                                  ┌─────────────────────┐
                                  │ tools.dispatch(...) │
                                  └──────────┬──────────┘
                                             │
                 ┌───────────────────────────┼─────────────────────┐
                 ▼                           ▼                     ▼
         MemoryStore.save       MemoryStore.search      tools.verify_citations
                 │                           │                     │
                 └──────────── SQLite ───────┘                     │
                                                                  ▼
                                                        (post-processes reply)
```

File responsibilities:

| File | Responsibility |
| --- | --- |
| `memory_store.py` | Only this module touches SQLite. Exposes `save / search / exists / count / get`. `search` uses deterministic token + tag overlap scoring (no embeddings, zero extra deps). |
| `tools.py` | LLM-agnostic JSON schema (OpenAI-style `{"type":"function","function":{...}}`), a dispatcher that returns structured errors instead of raising, and `verify_citations` — the deterministic hallucination guard. |
| `agent.py` | Gemini (`google-genai`) client, converts the JSON schema into `types.FunctionDeclaration`, runs the tool-use loop, and streams `[TOOL]` / `[VERIFY]` diagnostics to stderr. |

## Tool Schema Design

Two explicit verbs, one for writes and one for reads:

- **`save_memory(content, tags)`** — called when the user *states* a
  personal fact. The LLM rewrites the statement into first person
  and extracts 2–5 lowercase `tags` in the same tool call. Pushing
  tag extraction into the LLM is the single biggest retrieval-accuracy
  lever in this design: it lets `search_memory` beat simple keyword
  match without needing embeddings.
- **`search_memory(query, top_k=3)`** — called before *any* answer
  that could depend on user preferences. The description explicitly
  tells the model to admit ignorance on an empty result set.

Why split this way:

1. Verb-based names (`save` / `search`) give the model an obvious
   intent→tool mapping — statements pick the former, questions pick
   the latter.
2. Keeping the schema in plain JSON (not SDK-specific types) makes
   `tools.py` reusable across OpenAI / Gemini / Claude. `agent.py`
   is the only file that needs to change when swapping providers;
   it contains `_to_gemini_schema` which recursively converts the
   JSON schema into Gemini's `types.Schema`.
3. `dispatch` never raises. Bad tool calls come back as
   `{"error": "..."}` so the LLM sees the failure and can retry,
   rather than bubbling an exception into the REPL.

## Verification — how hallucinated citations are prevented

Verification is **a deterministic post-processing step, not a tool
the LLM can choose to skip**. The system-prompt rule requires every
memory reference to use the token `[memory:<id>]` whose `<id>` comes
from the most recent `search_memory` result. After the model
produces its final text reply, `tools.verify_citations(reply, store)`
runs:

1. `re.finditer(r"\[memory:(\d+)\]", reply)` extracts every cited id.
2. For each id, `MemoryStore.exists(id)` runs a `SELECT 1 FROM
   memories WHERE id = ?`. This is the ground-truth check — it does
   not consult the LLM.
3. If `exists()` returns `False`, the citation token is removed
   from the reply and a `[VERIFY] id=<n> status=fail` line is
   printed to stderr. Real citations emit `status=ok`.
4. The cleaned reply replaces the last assistant turn in history,
   so downstream model turns never see an invalid citation.

Because `exists` is a pure SQL lookup and `verify_citations` is
invoked unconditionally before returning, the model has no way to
bypass verification. A failed lookup is evidence that would appear
in `[VERIFY]` logs, satisfying the challenge's "backed by a failed
memory lookup" requirement for the unknown-fact path.

Example log output for the README §57-65 scenario:

```
[TOOL] save_memory args={"content":"I'm training for a marathon and hate running in the rain.","tags":["running","marathon","weather"]} result={"id":1,"status":"saved"}
[TOOL] save_memory args={"content":"My favorite recovery meal is congee with century egg.","tags":["food","recovery"]} result={"id":2,"status":"saved"}
[TOOL] search_memory args={"query":"post-run meal","top_k":3} result={"results":[{"id":2,"content":"...","tags":["food","recovery"],"score":4.0}]}
[VERIFY] id=2 status=ok
[TOOL] search_memory args={"query":"favorite color"} result={"results":[]}
```

The last line is the auditable "I don't know" evidence — an empty
`results` array grounds the refusal in a real failed lookup, not a
prompt instruction.

## Project Layout

```
CLI-base-Agent/
├── agent.py                  # CLI + Gemini tool-use loop
├── memory_store.py           # SQLite persistence + retrieval
├── tools.py                  # Schemas, dispatch, verify_citations
├── requirements.txt          # google-genai, python-dotenv
├── .env.example              # placeholders only, never real keys
├── DEVELOPMENT_PLAN.md       # high-level plan
├── EXECUTION_STEPS.md        # atomic steps + acceptance criteria
├── EXECUTION_LOG.md          # per-phase test results + notes
├── scripts/sync-ai-session.sh  # copies Cursor transcripts into ai-session/
├── ai-session/               # AI collaboration logs (MANDATORY deliverable)
└── tests/
    ├── test_memory_store.py  # 12 unit tests
    ├── test_tools.py         # 14 unit tests
    ├── test_agent.py         # 9 unit tests with mocked Gemini
    ├── test_scenario.py      # end-to-end, skipped without API key
    └── manual_replay.md      # hand-verify fallback
```
