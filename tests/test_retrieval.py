import os
import tempfile

import pytest

from app.ingestion.documents import build_chunks, chunk_text, validate_document
from app.storage.sqlite import DocumentRecord, SQLiteStore


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def test_chunk_text_short_text_returns_single_chunk():
    text = "This is a short document."
    chunks = chunk_text(text, chunk_size=1200, overlap=150)
    assert chunks == [text]


def test_chunk_text_long_text_splits_into_multiple_chunks():
    paragraph = "Sentence about latency and errors. " * 40  # ~1440 chars
    chunks = chunk_text(paragraph, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    # No chunk should wildly exceed the target size
    assert all(len(c) <= 400 for c in chunks)


def test_build_chunks_preserves_parent_document_identity():
    doc = {
        "document_id": "INC-9999",
        "title": "Test incident",
        "type": "incident_report",
        "service": "orders-api",
        "date": "2026-09-16",
        "version": "v2.8.1",
        "content": "Latency spike investigation. " * 100,
    }
    chunks = build_chunks(doc)
    assert len(chunks) >= 1
    for c in chunks:
        assert c["document_id"] == "INC-9999"
        assert c["service"] == "orders-api"
        assert c["chunk_id"].startswith("INC-9999::chunk-")


def test_validate_document_flags_missing_fields():
    errors = validate_document({"document_id": "X"})
    assert errors  # missing title/content

    errors_ok = validate_document(
        {"document_id": "X", "title": "T", "content": "C"}
    )
    assert errors_ok == []


# ---------------------------------------------------------------------------
# SQLite store
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_store():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        yield SQLiteStore(db_path=db_path)


def test_sqlite_upsert_and_get(tmp_store):
    record = DocumentRecord(
        document_id="INC-1",
        title="Test",
        type="incident_report",
        service="orders-api",
        date="2026-09-16",
        version="v2.8.1",
        content="content here",
    )
    tmp_store.upsert_document(record)

    fetched = tmp_store.get_document("INC-1")
    assert fetched is not None
    assert fetched["title"] == "Test"
    assert tmp_store.count() == 1

    # Upserting again with the same id should not create a duplicate
    tmp_store.upsert_document(record)
    assert tmp_store.count() == 1


def test_sqlite_metadata_filtering(tmp_store):
    tmp_store.upsert_document(
        DocumentRecord("A", "A title", "incident_report", "orders-api", "2026-09-16", "v2.8.1", "c")
    )
    tmp_store.upsert_document(
        DocumentRecord("B", "B title", "postmortem", "catalog-api", "2026-05-01", "v1.0.0", "c")
    )

    results = tmp_store.search_by_metadata(service="orders-api")
    assert len(results) == 1
    assert results[0]["document_id"] == "A"

    results_type = tmp_store.search_by_metadata(document_type="postmortem")
    assert len(results_type) == 1
    assert results_type[0]["document_id"] == "B"


# ---------------------------------------------------------------------------
# Hybrid ranking helper functions (pure logic, no external services)
# ---------------------------------------------------------------------------


def test_date_proximity_score_exact_and_far():
    from app.retrieval.hybrid import _date_proximity_score

    assert _date_proximity_score("2026-09-16", "2026-09-16") == 1.0
    assert _date_proximity_score("2020-01-01", "2026-09-16") < 0.1
    assert _date_proximity_score(None, "2026-09-16") == 0.0


def test_semantic_score_converts_distance():
    from app.retrieval.hybrid import _semantic_score

    assert _semantic_score(0.0) == 1.0
    assert _semantic_score(None) == 0.0
    assert 0.0 <= _semantic_score(0.5) <= 1.0
