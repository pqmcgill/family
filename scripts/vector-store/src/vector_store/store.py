"""LanceDB wrapper for the family vector store."""

from __future__ import annotations

from pathlib import Path

import lancedb
from sentence_transformers import SentenceTransformer

DEFAULT_STORE_PATH = Path(__file__).resolve().parents[4] / "data" / "vector_store"
DEFAULT_MODEL = "all-MiniLM-L6-v2"
TABLE_NAME = "chunks"


class VectorStore:
    """Manages embeddings in a local LanceDB instance."""

    def __init__(
        self,
        store_path: Path = DEFAULT_STORE_PATH,
        model_name: str = DEFAULT_MODEL,
    ):
        self.store_path = store_path
        self.db = lancedb.connect(str(store_path))
        self.model = SentenceTransformer(model_name)

    def _get_table(self) -> lancedb.table.Table:
        return self.db.open_table(TABLE_NAME)

    def has_data(self) -> bool:
        try:
            self._get_table()
            return True
        except Exception:
            return False

    def upsert(self, chunks: list[dict]) -> int:
        """Insert or replace chunks. Each chunk must have: id, text, source_file, date, type, domain.

        Chunks with the same id are replaced (delete + insert).
        Returns the number of chunks written.
        """
        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=False)

        records = []
        for chunk, embedding in zip(chunks, embeddings):
            records.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "source_file": chunk["source_file"],
                "date": chunk.get("date", ""),
                "type": chunk.get("type", ""),
                "domain": chunk.get("domain", ""),
                "vector": embedding,
            })

        if self.has_data():
            table = self._get_table()
            # Remove existing chunks from the same source files
            source_files = {r["source_file"] for r in records}
            for sf in source_files:
                try:
                    table.delete(f'source_file = "{sf}"')
                except Exception:
                    pass
            table.add(records)
        else:
            self.db.create_table(TABLE_NAME, data=records)

        return len(records)

    def search(
        self,
        query: str,
        limit: int = 10,
        filter_type: str | None = None,
        filter_domain: str | None = None,
    ) -> list[dict]:
        """Semantic search. Returns chunks sorted by relevance."""
        if not self.has_data():
            return []

        table = self._get_table()
        query_embedding = self.model.encode(query, show_progress_bar=False)

        q = table.search(query_embedding).limit(limit)

        if filter_type:
            q = q.where(f'type = "{filter_type}"')
        if filter_domain:
            q = q.where(f'domain = "{filter_domain}"')

        results = q.to_list()
        return [
            {
                "id": r["id"],
                "text": r["text"],
                "source_file": r["source_file"],
                "date": r["date"],
                "type": r["type"],
                "domain": r["domain"],
                "score": r.get("_distance", 0),
            }
            for r in results
        ]

    def status(self) -> dict:
        """Return stats about what's indexed."""
        if not self.has_data():
            return {"total_chunks": 0, "source_files": [], "types": {}}

        table = self._get_table()
        arrow_table = table.to_arrow()
        total = arrow_table.num_rows

        source_files = sorted(set(arrow_table.column("source_file").to_pylist()))

        type_list = arrow_table.column("type").to_pylist()
        type_counts: dict[str, int] = {}
        for t in type_list:
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_chunks": total,
            "source_files": source_files,
            "types": type_counts,
        }

    def clear(self) -> None:
        """Drop all data."""
        try:
            self.db.drop_table(TABLE_NAME)
        except Exception:
            pass
