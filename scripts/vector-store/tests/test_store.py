"""Tests for the VectorStore class."""

import pytest

from vector_store.store import VectorStore


@pytest.fixture
def store(tmp_path):
    """Create a VectorStore backed by a temp directory."""
    return VectorStore(store_path=tmp_path / "test_store")


def _make_chunks(n: int, source: str = "test.md", type_: str = "checkin", domain: str = "homeschool"):
    return [
        {
            "id": f"{source}::chunk_{i}",
            "text": f"Test chunk content number {i}",
            "source_file": source,
            "date": "2026-W14/mon",
            "type": type_,
            "domain": domain,
        }
        for i in range(n)
    ]


class TestUpsert:
    def test_insert_into_empty_store(self, store):
        chunks = _make_chunks(3)
        n = store.upsert(chunks)
        assert n == 3
        assert store.has_data()

    def test_empty_list_returns_zero(self, store):
        assert store.upsert([]) == 0

    def test_reindex_replaces_chunks_from_same_source(self, store):
        store.upsert(_make_chunks(3, source="a.md"))
        store.upsert(_make_chunks(2, source="a.md"))
        info = store.status()
        assert info["total_chunks"] == 2

    def test_different_sources_coexist(self, store):
        store.upsert(_make_chunks(2, source="a.md"))
        store.upsert(_make_chunks(3, source="b.md"))
        info = store.status()
        assert info["total_chunks"] == 5


class TestSearch:
    def test_search_returns_results(self, store):
        store.upsert([
            {"id": "1", "text": "homeschool math happened today", "source_file": "a.md", "date": "", "type": "checkin", "domain": "homeschool"},
            {"id": "2", "text": "laundry moved to dryer", "source_file": "a.md", "date": "", "type": "checkin", "domain": "laundry"},
        ])
        results = store.search("math class", limit=1)
        assert len(results) == 1
        assert "math" in results[0]["text"]

    def test_search_empty_store(self, store):
        assert store.search("anything") == []

    def test_search_filter_by_type(self, store):
        store.upsert([
            {"id": "1", "text": "a checkin about laundry", "source_file": "a.md", "date": "", "type": "checkin", "domain": "laundry"},
            {"id": "2", "text": "laundry pipeline state", "source_file": "b.md", "date": "", "type": "state", "domain": "laundry"},
        ])
        results = store.search("laundry", limit=5, filter_type="state")
        assert all(r["type"] == "state" for r in results)

    def test_search_filter_by_domain(self, store):
        store.upsert([
            {"id": "1", "text": "homeschool math today", "source_file": "a.md", "date": "", "type": "checkin", "domain": "homeschool"},
            {"id": "2", "text": "math standards coverage", "source_file": "b.md", "date": "", "type": "coverage", "domain": "math"},
        ])
        results = store.search("math", limit=5, filter_domain="homeschool")
        assert all(r["domain"] == "homeschool" for r in results)

    def test_search_result_fields(self, store):
        store.upsert([
            {"id": "test::1", "text": "some content", "source_file": "file.md", "date": "2026-W14", "type": "checkin", "domain": "meals"},
        ])
        results = store.search("content", limit=1)
        r = results[0]
        assert r["id"] == "test::1"
        assert r["source_file"] == "file.md"
        assert r["date"] == "2026-W14"
        assert r["type"] == "checkin"
        assert r["domain"] == "meals"
        assert "score" in r


class TestStatus:
    def test_empty_store(self, store):
        info = store.status()
        assert info["total_chunks"] == 0
        assert info["source_files"] == []
        assert info["types"] == {}

    def test_status_counts(self, store):
        store.upsert(_make_chunks(3, source="a.md", type_="checkin"))
        store.upsert(_make_chunks(2, source="b.md", type_="state"))
        info = store.status()
        assert info["total_chunks"] == 5
        assert info["types"]["checkin"] == 3
        assert info["types"]["state"] == 2
        assert set(info["source_files"]) == {"a.md", "b.md"}


class TestClear:
    def test_clear_removes_all_data(self, store):
        store.upsert(_make_chunks(5))
        store.clear()
        assert not store.has_data()
        assert store.status()["total_chunks"] == 0

    def test_clear_empty_store_is_noop(self, store):
        store.clear()  # should not raise
