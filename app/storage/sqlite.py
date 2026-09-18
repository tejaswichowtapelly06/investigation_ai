"""
SQLite storage for document metadata + raw content.

This is the source of truth for structured metadata (service, date, version,
type) and is used for metadata-filtered retrieval. Chroma is used only for
semantic search over chunk embeddings; the full document record always lives
here.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT,
    service TEXT,
    date TEXT,
    version TEXT,
    content TEXT NOT NULL,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_service ON documents(service);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type);
CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(date);
CREATE INDEX IF NOT EXISTS idx_documents_version ON documents(version);
"""


@dataclass
class DocumentRecord:
    document_id: str
    title: str
    type: Optional[str]
    service: Optional[str]
    date: Optional[str]
    version: Optional[str]
    content: str
    source: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "type": self.type,
            "service": self.service,
            "date": self.date,
            "version": self.version,
            "content": self.content,
            "source": self.source,
        }


class SQLiteStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def upsert_document(self, doc: DocumentRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (document_id, title, type, service, date, version, content, source)
                VALUES (:document_id, :title, :type, :service, :date, :version, :content, :source)
                ON CONFLICT(document_id) DO UPDATE SET
                    title=excluded.title,
                    type=excluded.type,
                    service=excluded.service,
                    date=excluded.date,
                    version=excluded.version,
                    content=excluded.content,
                    source=excluded.source
                """,
                doc.to_dict(),
            )

    def upsert_documents(self, docs: Iterable[DocumentRecord]) -> int:
        count = 0
        for doc in docs:
            self.upsert_document(doc)
            count += 1
        return count

    def get_document(self, document_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_documents(self, document_ids: Iterable[str]) -> list[dict]:
        ids = list(document_ids)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM documents WHERE document_id IN ({placeholders})", ids
            ).fetchall()
            return [dict(r) for r in rows]

    def all_documents(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM documents").fetchall()
            return [dict(r) for r in rows]

    def search_by_metadata(
        self,
        service: Optional[str] = None,
        document_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        version: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        clauses = []
        params: list = []

        if service:
            clauses.append("LOWER(service) = LOWER(?)")
            params.append(service)
        if document_type:
            clauses.append("LOWER(type) = LOWER(?)")
            params.append(document_type)
        if version:
            clauses.append("version = ?")
            params.append(version)
        if date_from:
            clauses.append("date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("date <= ?")
            params.append(date_to)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM documents {where} ORDER BY date DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()
            return row["c"] if row else 0


_store: Optional[SQLiteStore] = None


def get_store() -> SQLiteStore:
    global _store
    if _store is None:
        _store = SQLiteStore()
    return _store
