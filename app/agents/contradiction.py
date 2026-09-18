"""
Contradiction Detection Agent.

Compares evidence documents (especially guidance/procedure documents of the
same type/topic but different dates or versions) and flags genuine conflicts
- not just differences in wording.
"""
from __future__ import annotations

import json

from app.llm.client import LLMError, get_llm_client

CONTRADICTION_SYSTEM = """You review a set of evidence documents from an internal engineering \
knowledge base to find genuine CONTRADICTIONS - cases where two documents give conflicting guidance, \
conflicting facts, or conflicting recommended actions about the same subject.

Do not flag documents as contradictory just because they cover different topics or incidents. Only \
flag actual conflicts (e.g. one document says to do X, another says not to do X in the same situation; \
or documents disagree on a fact).

When a conflict exists between differently-dated or differently-versioned documents, note which is \
newer, but only state that the newer one supersedes the older one if the documents themselves indicate \
that (e.g. the newer doc explicitly updates/replaces the guidance, or is clearly a revised procedure \
for the same scenario). Otherwise, present both sides and note the ambiguity rather than picking one \
as correct.

Respond with ONLY a JSON object:
{
  "contradictions": [
    {
      "title": string,          // short label for the conflict
      "description": string,    // 1-3 sentences explaining what conflicts, citing document IDs, dates and/or versions naturally
      "document_ids": [string]  // the documents involved
    }
  ]
}

If there are no genuine contradictions, respond with {"contradictions": []}."""


def detect_contradictions(evidence: list[dict]) -> list[dict]:
    if len(evidence) < 2:
        return []

    client = get_llm_client()

    def _slim(d: dict) -> dict:
        return {
            "document_id": d.get("document_id"),
            "title": d.get("title"),
            "type": d.get("type"),
            "date": d.get("date"),
            "version": d.get("version"),
            "content": (d.get("content") or "")[:1000],
        }

    payload = {"documents": [_slim(d) for d in evidence]}

    try:
        result = client.complete_json(system=CONTRADICTION_SYSTEM, user=json.dumps(payload), max_tokens=1200)
        raw = result.get("contradictions", [])
        contradictions = []
        for c in raw:
            title = c.get("title")
            description = c.get("description")
            if title and description:
                contradictions.append(
                    {
                        "title": title,
                        "description": description,
                        "document_ids": c.get("document_ids", []),
                    }
                )
        return contradictions
    except LLMError:
        return []
