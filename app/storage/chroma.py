"""
ChromaDB-backed vector store for semantic search over document chunks.

Embeddings are generated locally with sentence-transformers
(BAAI/bge-small-en-v1.5 by default) - no external embedding API is used.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.config import settings

_embedder = None
_chroma_client = None
_collection = None


def get_embedder():
    """Lazily load the sentence-transformers embedding model."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(list(texts), normalize_embeddings=True)
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]


def get_collection():
    """Lazily initialize the persistent Chroma client/collection."""
    global _chroma_client, _collection
    if _collection is None:
        import chromadb

        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = _chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def reset_collection():
    """Used by tests / re-ingestion to start from a clean collection."""
    global _chroma_client, _collection
    import chromadb

    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
    try:
        _chroma_client.delete_collection(settings.chroma_collection_name)
    except Exception:
        pass
    _collection = _chroma_client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def upsert_chunks(chunks: list[dict]) -> None:
    """
    chunks: list of dicts with keys:
        chunk_id, document_id, title, type, service, date, version, content
    """
    if not chunks:
        return
    collection = get_collection()
    ids = [c["chunk_id"] for c in chunks]
    documents = [c["content"] for c in chunks]
    metadatas = [
        {
            "document_id": c["document_id"],
            "title": c.get("title") or "",
            "type": c.get("type") or "",
            "service": c.get("service") or "",
            "date": c.get("date") or "",
            "version": c.get("version") or "",
        }
        for c in chunks
    ]
    embeddings = embed_texts(documents)
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)


def semantic_search(query: str, top_k: int = 10, where: Optional[dict] = None) -> list[dict]:
    """
    Returns a list of dicts: {chunk_id, document_id, title, type, service,
    date, version, content, distance}
    """
    collection = get_collection()
    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query])[0]
    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=min(top_k, max(collection.count(), 1)),
    )
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    out = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(ids)

    for i, chunk_id in enumerate(ids):
        meta = metas[i] or {}
        out.append(
            {
                "chunk_id": chunk_id,
                "document_id": meta.get("document_id"),
                "title": meta.get("title"),
                "type": meta.get("type"),
                "service": meta.get("service") or None,
                "date": meta.get("date") or None,
                "version": meta.get("version") or None,
                "content": docs[i],
                "distance": dists[i],
            }
        )
    return out
