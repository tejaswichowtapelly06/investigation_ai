"""
Tests for graph node logic and decision routing. LLM-backed agent functions
are monkeypatched so these tests run deterministically without a live
ANTHROPIC_API_KEY or network access.
"""
from app.agents import analyzer
from app.graph.workflow import decide_next, _docs_to_evidence


def test_docs_to_evidence_sorts_by_score():
    docs = {
        "A": {"document_id": "A", "title": "a", "type": "t", "content": "c", "_score": 0.2},
        "B": {"document_id": "B", "title": "b", "type": "t", "content": "c", "_score": 0.9},
    }
    evidence = _docs_to_evidence(docs)
    assert [e["document_id"] for e in evidence] == ["B", "A"]


def test_decide_next_stops_at_max_iterations():
    state = {"iteration": 3, "max_iterations": 3, "needs_more_evidence": True, "gaps": ["x"]}
    assert decide_next(state) == "answer"


def test_decide_next_continues_when_gaps_and_budget_remain():
    state = {"iteration": 1, "max_iterations": 3, "needs_more_evidence": True, "gaps": ["x"]}
    assert decide_next(state) == "search_again"


def test_decide_next_stops_when_no_gaps():
    state = {"iteration": 1, "max_iterations": 3, "needs_more_evidence": False, "gaps": []}
    assert decide_next(state) == "answer"


def test_build_timeline_sorts_chronologically_and_skips_undated():
    docs = [
        {"document_id": "B", "title": "b", "type": "t", "date": "2026-09-16", "version": None, "content": "c2"},
        {"document_id": "A", "title": "a", "type": "t", "date": "2026-09-15", "version": None, "content": "c1"},
        {"document_id": "C", "title": "c", "type": "t", "date": None, "version": None, "content": "c3"},
    ]
    timeline = analyzer.build_timeline(docs)
    assert [t["document_id"] for t in timeline] == ["A", "B"]


def test_similar_incidents_node_skips_when_not_requested(monkeypatch):
    from app.graph.workflow import similar_incidents_node

    state = {
        "question": "Why did the Order API become slow?",
        "entities": {"investigation_targets": [], "requested_comparisons": []},
        "evidence": [
            {"document_id": "A", "title": "a", "type": "t", "date": "2026-09-16", "content": "c"},
        ],
        "investigation_steps": [],
    }
    result = similar_incidents_node(state)
    assert result["similar_incidents"] == []


def test_similar_incidents_node_runs_when_comparison_requested(monkeypatch):
    from app.graph import workflow

    def fake_analyze_similar_incidents(question, current, candidates):
        return [
            {
                "document_id": candidates[0]["document_id"],
                "classification": "similar_incident",
                "reasoning": "same service, different root cause",
            }
        ]

    monkeypatch.setattr(analyzer, "analyze_similar_incidents", fake_analyze_similar_incidents)
    monkeypatch.setattr(workflow.analyzer, "analyze_similar_incidents", fake_analyze_similar_incidents)

    state = {
        "question": "Have we seen this before?",
        "entities": {
            "investigation_targets": ["previous similar incidents"],
            "requested_comparisons": [],
            "date": "2026-09-16",
            "service": "orders-api",
        },
        "evidence": [
            {
                "document_id": "INC-1042",
                "title": "current",
                "type": "incident_report",
                "date": "2026-09-16",
                "service": "orders-api",
                "content": "current incident",
            },
            {
                "document_id": "PM-211",
                "title": "past",
                "type": "postmortem",
                "date": "2026-05-03",
                "service": "orders-api",
                "content": "past incident, different cause",
            },
        ],
        "investigation_steps": [],
    }

    result = workflow.similar_incidents_node(state)
    assert len(result["similar_incidents"]) == 1
    assert result["similar_incidents"][0]["document_id"] == "PM-211"
    assert result["similar_incidents"][0]["classification"] == "similar_incident"
