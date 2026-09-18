from __future__ import annotations

from typing import Optional

from app.storage.chroma import semantic_search as _semantic_search


def semantic_retrieve(
    query: str,
    top_k: int = 10,
    service: Optional[str] = None
) -> list[dict]:
    """
    Semantic search over document chunks.

    Service is NOT used as a hard Chroma filter.
    Instead, semantic results are retrieved first and service
    relevance is applied afterward.
    """

    # Get semantic results without filtering by service
    results = _semantic_search(
        query,
        top_k=top_k,
        where=None
    )

    # No service specified → return normal semantic results
    if not service:
        return results

    # Normalize the requested service
    requested_service = (
        service.lower()
        .strip()
        .replace("_", "-")
        .replace(" ", "-")
    )

    # Give matching services a ranking boost
    for result in results:
        metadata = result.get("metadata", {})
        doc_service = metadata.get("service", "")

        normalized_doc_service = (
            str(doc_service)
            .lower()
            .strip()
            .replace("_", "-")
            .replace(" ", "-")
        )

        if requested_service == normalized_doc_service:
            result["score"] = result.get("score", 0) + 0.2

    # Re-sort after applying service relevance
    results.sort(
        key=lambda x: x.get("score", 0),
        reverse=True
    )

    return results