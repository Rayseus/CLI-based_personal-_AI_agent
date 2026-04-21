"""Persistent memory store backed by SQLite.

The store is the single source of truth for user facts. It is
deliberately minimal: only `save`, `search`, `exists`, and `count`
are exposed so the rest of the agent has a tiny, auditable surface
area that the deterministic verifier can reason about.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Iterable


_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+")

_STOP = {
    "i", "a", "an", "the", "and", "or", "but", "for", "to", "in", "on",
    "of", "at", "by", "with", "is", "am", "are", "was", "were", "be",
    "been", "being", "do", "does", "did", "doing", "have", "has", "had",
    "having", "it", "its", "this", "that", "these", "those", "my", "your",
    "our", "their", "me", "you", "he", "she", "we", "they", "s", "t", "m",
    "re", "ve", "ll", "d", "if", "so", "as", "about", "what", "when",
    "where", "which", "who", "how", "should", "shall", "will", "can",
    "could", "would", "may", "might", "must", "some", "any", "no", "not",
    "yes", "too", "also", "just", "only", "then", "favorite", "favourite",
    "like", "love", "good", "best", "thing", "things", "want", "get",
}


def _tokenize(text: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text or "")
        if t.lower() not in _STOP
    ]


def _prefix_overlap(q_tokens: set[str], c_tokens: set[str]) -> float:
    """Score token overlap allowing length-3+ prefix matches.

    Exact match counts 1.0; a prefix relation (either direction) counts
    0.5. Each query token contributes at most once. This handles
    morphological variants like ``rain <-> rainy`` and ``run <-> running``
    without pulling in a stemmer dependency.
    """
    score = 0.0
    for qt in q_tokens:
        if qt in c_tokens:
            score += 1.0
            continue
        if len(qt) < 3:
            continue
        for ct in c_tokens:
            if len(ct) < 3:
                continue
            if qt.startswith(ct) or ct.startswith(qt):
                score += 0.5
                break
    return score


class MemoryStore:
    """Thin wrapper around a local SQLite file."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                content    TEXT NOT NULL,
                tags       TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def save(self, content: str, tags: Iterable[str] | None = None) -> int:
        if not content or not content.strip():
            raise ValueError("content must be a non-empty string")
        tags_list = [str(t).strip().lower() for t in (tags or []) if str(t).strip()]
        cur = self._conn.execute(
            "INSERT INTO memories (content, tags, created_at) VALUES (?, ?, ?)",
            (
                content.strip(),
                json.dumps(tags_list, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def exists(self, memory_id) -> bool:
        if not isinstance(memory_id, int) or isinstance(memory_id, bool):
            try:
                memory_id = int(memory_id)
            except (TypeError, ValueError):
                return False
        row = self._conn.execute(
            "SELECT 1 FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return row is not None

    def get(self, memory_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT id, content, tags, created_at FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "content": row["content"],
            "tags": json.loads(row["tags"]),
            "created_at": row["created_at"],
        }

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
        return int(row["c"])

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Score-based keyword + tag retrieval.

        No embeddings: we stay deterministic and dependency-free.
        - token overlap between query and content contributes weight 1.0 per hit
        - tag overlap contributes weight 2.0 per hit (tags are curated by the LLM)
        Entries with score == 0 are dropped; results are sorted by score desc,
        then id desc so newer memories win ties.
        """
        q_tokens = set(_tokenize(query))
        if not q_tokens:
            return []
        rows = self._conn.execute(
            "SELECT id, content, tags FROM memories"
        ).fetchall()
        scored: list[tuple[float, dict]] = []
        for row in rows:
            content_tokens = set(_tokenize(row["content"]))
            tags = json.loads(row["tags"])
            tag_tokens = {t.lower() for t in tags if t.lower() not in _STOP}
            content_hits = _prefix_overlap(q_tokens, content_tokens)
            tag_hits = _prefix_overlap(q_tokens, tag_tokens)
            score = content_hits * 1.0 + tag_hits * 2.0
            if score > 0:
                scored.append(
                    (
                        score,
                        {
                            "id": row["id"],
                            "content": row["content"],
                            "tags": tags,
                            "score": score,
                        },
                    )
                )
        scored.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)
        return [item for _, item in scored[:top_k]]
