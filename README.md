# CLI-base-Agent: Multi-Tool CLI Agent with Persistent Memory & Verification

# Implementation

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
