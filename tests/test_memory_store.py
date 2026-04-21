"""Unit tests for MemoryStore covering Step 1.1 - 1.4."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from memory_store import MemoryStore  # noqa: E402


class _TempDBMixin:
    def _new_store(self) -> MemoryStore:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.addCleanup(lambda p=tmp.name: os.path.exists(p) and os.remove(p))
        store = MemoryStore(tmp.name)
        self.addCleanup(store.close)
        return store


class TestSchemaAndPersistence(unittest.TestCase, _TempDBMixin):
    def test_TC_1_1_1_creates_table(self) -> None:
        store = self._new_store()
        self.assertEqual(store.count(), 0)
        store.save("hello", ["greet"])
        self.assertEqual(store.count(), 1)

    def test_TC_1_1_2_reopen_preserves_data(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.addCleanup(lambda p=tmp.name: os.path.exists(p) and os.remove(p))

        for _ in range(10):
            s = MemoryStore(tmp.name)
            s.close()

        s = MemoryStore(tmp.name)
        try:
            s.save("persisted", ["misc"])
        finally:
            s.close()

        s = MemoryStore(tmp.name)
        try:
            self.assertEqual(s.count(), 1)
        finally:
            s.close()


class TestSave(unittest.TestCase, _TempDBMixin):
    def test_TC_1_2_1_incrementing_ids(self) -> None:
        store = self._new_store()
        self.assertEqual(store.save("hello", ["greet"]), 1)
        self.assertEqual(store.save("world", []), 2)

    def test_TC_1_2_2_empty_raises(self) -> None:
        store = self._new_store()
        with self.assertRaises(ValueError):
            store.save("", ["x"])
        with self.assertRaises(ValueError):
            store.save("   ", ["x"])

    def test_TC_1_2_3_tags_roundtrip(self) -> None:
        store = self._new_store()
        mid = store.save("hello there", ["Greet", " "])
        row = store.get(mid)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["tags"], ["greet"])
        self.assertEqual(row["content"], "hello there")


class TestSearch(unittest.TestCase, _TempDBMixin):
    def test_TC_1_3_1_empty_store(self) -> None:
        store = self._new_store()
        self.assertEqual(store.search("anything"), [])

    def test_TC_1_3_2_matches_content_and_tags(self) -> None:
        store = self._new_store()
        store.save("I'm training for a marathon", ["running", "goals"])
        hits = store.search("marathon")
        self.assertEqual(len(hits), 1)
        self.assertIn("marathon", hits[0]["content"].lower())

    def test_TC_1_3_3_returns_empty_for_unknown(self) -> None:
        store = self._new_store()
        store.save("I'm training for a marathon", ["running"])
        self.assertEqual(store.search("favorite color"), [])

    def test_TC_1_3_4_sorted_by_score(self) -> None:
        store = self._new_store()
        low_id = store.save("I like apples", ["fruit"])
        high_id = store.save(
            "I love congee recovery after a long run", ["food", "recovery", "run"]
        )
        hits = store.search("recovery run", top_k=5)
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0]["id"], high_id)
        if len(hits) >= 2:
            self.assertGreaterEqual(hits[0]["score"], hits[1]["score"])
        self.assertNotEqual(hits[0]["id"], low_id)


class TestExists(unittest.TestCase, _TempDBMixin):
    def test_TC_1_4_1_returns_true(self) -> None:
        store = self._new_store()
        mid = store.save("fact", ["x"])
        self.assertTrue(store.exists(mid))

    def test_TC_1_4_2_returns_false(self) -> None:
        store = self._new_store()
        self.assertFalse(store.exists(999))

    def test_TC_1_4_3_non_int_returns_false(self) -> None:
        store = self._new_store()
        self.assertFalse(store.exists("abc"))
        self.assertFalse(store.exists(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
