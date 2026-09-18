"""
Final Answer Generation Agent.
"""
from __future__ import annotations

import json

from app.llm.client import LLMError, get_llm_client

ANSWER_SYSTEM = """You are writing the final answer for an internal engineering investigation \
assistant. You are given the original question and everything the investigation discovered: evidence \
documents, a timeline, contradictions, similar-incident comparisons, and any unresolved gaps.

Write an answer that:
  1. Directly answers the question.
  2. Explains the reasoning, citing document IDs naturally in prose (e.g. "INC-1042 reports...").
  3. Mentions relevant dates and versions when they matter to the reasoning.
  4. Explains any contradictions rather than silently picking one side.
  5. Explicitly states uncertainty or gaps where the evidence does not fully answer the question.
  6. NEVER invents documents, dates, versions, or facts not present in the provided evidence.
  7. If the evidence is insufficient to answer the question (e.g. no matching documents, or the \
documents describe different services/failure mechanisms than what's being asked about), say so \
plainly instead of guessing.

Also decide a confidence level for the answer, based on evidence quality (not how the answer "feels"):
  - "high": strong, direct, unambiguous evidence for the core claims
  - "medium": reasonable evidence but with some gaps, indirect inference, or minor ambiguity
  - "low": thin or tangential evidence; the answer is a best guess
  - "insufficient": the evidence does not meaningfully address the question (e.g. no relevant documents, \
or the retrieved documents describe unrelated services/mechanisms)

Respond with ONLY a JSON object:
{
  "answer": string,       // the full prose answer, several sentences to a short paragraph
  "confidence": "high" | "medium" | "low" | "insufficient"
}"""


def generate_answer(
    question: str,
    entities: dict,
    evidence: list[dict],
    contradictions: list[dict],
    timeline: list[dict],
    similar_incidents: list[dict],
    gaps: list[str],
) -> dict:
    client = get_llm_client()

    def _slim(d: dict) -> dict:
        return {
            "document_id": d.get("document_id"),
            "title": d.get("title"),
            "type": d.get("type"),
            "service": d.get("service"),
            "date": d.get("date"),
            "version": d.get("version"),
            "content": (d.get("content") or "")[:1200],
        }

    payload = {
        "question": question,
        "entities": entities,
        "evidence": [_slim(d) for d in evidence],
        "timeline": timeline,
        "contradictions": contradictions,
        "similar_incidents": similar_incidents,
        "unresolved_gaps": gaps,
    }

    if not evidence:
        return {
            "answer": (
                "No relevant documents were found for this question. The available document set does "
                "not contain evidence that addresses it, so no evidence-backed answer can be given."
            ),
            "confidence": "insufficient",
        }

    try:
        result = client.complete_json(system=ANSWER_SYSTEM, user=json.dumps(payload), max_tokens=1500)
        answer = result.get("answer", "").strip()
        confidence = result.get("confidence", "").strip().lower()
        if confidence not in {"high", "medium", "low", "insufficient"}:
            confidence = "low" if answer else "insufficient"
        if not answer:
            answer = "The investigation could not produce a grounded answer from the available evidence."
            confidence = "insufficient"
        return {"answer": answer, "confidence": confidence}
    except LLMError as exc:
        return {
            "answer": (
                "The investigation gathered evidence, but the final answer could not be generated due "
                f"to an LLM error ({exc}). Please review the evidence and trace below."
            ),
            "confidence": "insufficient",
        }
