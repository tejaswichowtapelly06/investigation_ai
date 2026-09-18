"""
Ingestion pipeline.

Usage:
    python -m app.ingestion.documents [--reset]

Loads data/documents.json, validates each record, stores metadata/content in
SQLite, chunks the content, generates embeddings, and upserts the chunks into
ChromaDB. Re-running ingestion is idempotent: SQLite uses an upsert on
document_id, and Chroma chunk ids are deterministic (document_id + chunk
index), so re-ingesting the same document overwrites rather than duplicates.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from app.config import settings
from app.storage.chroma import reset_collection, upsert_chunks
from app.storage.sqlite import DocumentRecord, SQLiteStore


REQUIRED_FIELDS = {"document_id", "title", "content"}
OPTIONAL_FIELDS = {"type", "service", "date", "version", "source"}


def load_documents(path: Optional[str] = None) -> list[dict]:
    doc_path = Path(path or settings.documents_path)
    if not doc_path.exists():
        raise FileNotFoundError(f"documents.json not found at {doc_path}")
    with open(doc_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError("documents.json must contain a JSON array of document objects")
    return raw


def validate_document(doc: dict) -> list[str]:
    """Return a list of validation error strings (empty list = valid)."""
    errors = []
    missing = REQUIRED_FIELDS - doc.keys()
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")
    if not str(doc.get("document_id", "")).strip():
        errors.append("document_id must be a non-empty string")
    if not str(doc.get("content", "")).strip():
        errors.append("content must be a non-empty string")
    return errors


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple character-based sliding window chunker with paragraph awareness."""
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        # try to break on a paragraph/sentence boundary near the end
        if end < length:
            boundary = text.rfind("\n\n", start, end)
            if boundary == -1 or boundary <= start + chunk_size // 2:
                boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks(doc: dict) -> list[dict]:
    pieces = chunk_text(doc["content"], settings.chunk_size, settings.chunk_overlap)
    if not pieces:
        pieces = [doc["content"]]

    chunks = []
    for idx, piece in enumerate(pieces):
        chunks.append(
            {
                "chunk_id": f"{doc['document_id']}::chunk-{idx}",
                "document_id": doc["document_id"],
                "title": doc.get("title"),
                "type": doc.get("type"),
                "service": doc.get("service"),
                "date": doc.get("date"),
                "version": doc.get("version"),
                "content": piece,
            }
        )
    return chunks


def ingest(path: Optional[str] = None, reset: bool = False, store: Optional[SQLiteStore] = None) -> dict:
    documents = load_documents(path)
    store = store or SQLiteStore()

    if reset:
        reset_collection()

    ingested, skipped, all_chunks = 0, [], []

    for doc in documents:
        errors = validate_document(doc)
        if errors:
            skipped.append({"document_id": doc.get("document_id", "<unknown>"), "errors": errors})
            continue

        record = DocumentRecord(
            document_id=str(doc["document_id"]),
            title=str(doc["title"]),
            type=doc.get("type"),
            service=doc.get("service"),
            date=doc.get("date"),
            version=doc.get("version"),
            content=str(doc["content"]),
            source=doc.get("source"),
        )
        store.upsert_document(record)
        all_chunks.extend(build_chunks(doc))
        ingested += 1

    if all_chunks:
        upsert_chunks(all_chunks)

    return {
        "ingested_documents": ingested,
        "skipped_documents": skipped,
        "chunks_indexed": len(all_chunks),
        "total_documents_in_store": store.count(),
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest documents.json into SQLite + Chroma")
    parser.add_argument("--path", default=None, help="Path to documents.json")
    parser.add_argument("--reset", action="store_true", help="Reset the Chroma collection before ingesting")
    args = parser.parse_args()

    result = ingest(path=args.path, reset=args.reset)
    print(json.dumps(result, indent=2))
    if result["skipped_documents"]:
        print(f"WARNING: {len(result['skipped_documents'])} document(s) skipped due to validation errors", file=sys.stderr)


if __name__ == "__main__":
    main()
