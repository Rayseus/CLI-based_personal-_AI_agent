"""Tool schemas, dispatcher, and deterministic citation verifier.

Design notes
------------
- Two explicit LLM tools: `save_memory` and `search_memory`. The names
  are verbs so the model reliably picks one based on the user's
  intent (statement vs. question).
- `verify_citations` is NOT exposed to the LLM. Verification is a
  post-processing step that runs unconditionally on every final
  assistant message, so the LLM cannot skip or bypass it.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from memory_store import MemoryStore


SAVE_MEMORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "description": (
            "Store a fact the user told about themselves (preference, goal, "
            "habit, personal history). Call this IMMEDIATELY when the user "
            "states such a fact. Do not call it for questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The full statement, rewritten in first person, "
                        "preserving all specific details."
                    ),
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "2-5 lowercase topical keywords to help future "
                        "retrieval (e.g. ['running','weather'])."
                    ),
                },
            },
            "required": ["content", "tags"],
        },
    },
}


SEARCH_MEMORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_memory",
        "description": (
            "Retrieve relevant stored memories. MUST be called before "
            "answering any question that depends on user preferences, "
            "history, goals, or habits. Returns an empty list if nothing "
            "relevant is stored — in that case you MUST admit you don't "
            "know instead of guessing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language query describing what to recall.",
                },
                "top_k": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
}


TOOL_SCHEMAS = [SAVE_MEMORY_SCHEMA, SEARCH_MEMORY_SCHEMA]


def _missing_field(fields: list[str], arguments: dict) -> str | None:
    for f in fields:
        if f not in arguments:
            return f
    return None


def dispatch(tool_name: str, arguments: dict, store: MemoryStore) -> dict:
    """Route an LLM tool_call to the memory store.

    Returns a JSON-serializable dict. Errors are returned as
    ``{"error": "..."}`` instead of raised, so the LLM can see and
    recover from bad tool calls.
    """
    if not isinstance(arguments, dict):
        return {"error": "arguments must be an object"}

    if tool_name == "save_memory":
        missing = _missing_field(["content", "tags"], arguments)
        if missing:
            return {"error": f"missing field: {missing}"}
        content = arguments.get("content", "")
        tags = arguments.get("tags", [])
        if not isinstance(tags, list):
            return {"error": "tags must be an array of strings"}
        try:
            new_id = store.save(content, tags)
        except ValueError as e:
            return {"error": str(e)}
        return {"id": new_id, "status": "saved"}

    if tool_name == "search_memory":
        missing = _missing_field(["query"], arguments)
        if missing:
            return {"error": f"missing field: {missing}"}
        query = arguments.get("query", "")
        top_k = int(arguments.get("top_k", 3) or 3)
        top_k = max(1, min(top_k, 10))
        results = store.search(query, top_k=top_k)
        return {"results": results}

    return {"error": f"unknown tool: {tool_name}"}


_CITATION_RE = re.compile(r"\[memory:(\d+)\]")


def verify_citations(
    reply: str, store: MemoryStore
) -> tuple[str, list[dict]]:
    """Strip any `[memory:<id>]` whose id does not exist in the store.

    Returns (cleaned_reply, log) where ``log`` is a list of
    ``{"id": int, "status": "ok"|"fail"}`` entries, one per citation
    encountered. The verifier is deterministic and does not consult
    the LLM — that is the whole point.
    """
    if not reply:
        return reply or "", []

    log: list[dict] = []

    def _replace(match: re.Match) -> str:
        raw_id = match.group(1)
        mid = int(raw_id)
        if store.exists(mid):
            log.append({"id": mid, "status": "ok"})
            return match.group(0)
        log.append({"id": mid, "status": "fail"})
        return ""

    cleaned = _CITATION_RE.sub(_replace, reply)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, log


__all__ = [
    "TOOL_SCHEMAS",
    "SAVE_MEMORY_SCHEMA",
    "SEARCH_MEMORY_SCHEMA",
    "dispatch",
    "verify_citations",
]
