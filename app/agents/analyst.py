import logging
from typing import Dict, Any, List
from app.graph.state import InvestigationState, InvestigationPlan
from app.tools.tool_registry import get_tool_registry
from app.tools.interfaces import DocumentResult
from datetime import datetime

logger = logging.getLogger(__name__)


def get_timestamp() -> str:
    """Get current timestamp for logging."""
    return datetime.now().isoformat()


def analyst_agent(state: InvestigationState, tool_registry=None) -> InvestigationState:
    """
    Evidence Analyst Agent: Analyzes retrieved documents, compares incidents,
    detects contradictions, and determines if evidence is sufficient.
    Uses dependency injection for evidence tools.
    
    Args:
        state: Current investigation state
        tool_registry: ToolRegistry instance for dependency injection (optional, uses global for backward compatibility)
    """
    logger.info("=" * 60)
    logger.info("ANALYST AGENT - Starting evidence analysis")
    logger.info("=" * 60)
    
    retrieved_documents = state.get("retrieved_documents", [])
    logger.info(f"ANALYST - Analyzing {len(retrieved_documents)} retrieved documents")
    
    if not retrieved_documents:
        logger.warning("ANALYST - No documents to analyze")
        state["evidence_sufficient"] = False
        state["findings"] = ["No documents retrieved for analysis"]
        state["contradictions"] = []
        state["related_incidents"] = []
        state["evidence"] = []
        state["evidence_gaps"] = []
        
        logger.info("ANALYST AGENT - Completed (no documents)")
        logger.info("=" * 60)
        return state
    
    # Get evidence tool from registry (dependency injection)
    try:
        if tool_registry is None:
            # Fallback to global registry for backward compatibility
            from app.tools.tool_registry import get_tool_registry
            tool_registry = get_tool_registry()
            logger.warning("ANALYST - Using global registry (deprecated, pass tool_registry parameter)")
        
        evidence_tool = tool_registry.get_evidence_tool()
        logger.info("ANALYST - Using injected evidence tool")
    except ValueError as e:
        logger.error(f"ANALYST - No evidence tool registered: {e}")
        state["evidence_sufficient"] = False
        state["findings"] = ["Error: No evidence tool available"]
        state["contradictions"] = []
        state["related_incidents"] = []
        state["evidence"] = []
        state["evidence_gaps"] = []
        return state
    
    # Convert dict documents to DocumentResult objects
    document_results = convert_to_document_results(retrieved_documents)
    
    # Extract evidence claims using injected tool
    try:
        evidence = evidence_tool.extract_evidence(document_results)
        state["evidence"] = evidence
        logger.info(f"ANALYST - Extracted {len(evidence)} evidence claims")
    except Exception as e:
        logger.error(f"ANALYST - Error extracting evidence claims: {e}")
        evidence = []
        state["evidence"] = []
    
    # Detect contradictions using injected tool
    try:
        contradictions = evidence_tool.detect_contradictions(document_results)
        state["contradictions"] = contradictions
        logger.info(f"ANALYST - Found {len(contradictions)} contradictions")
    except Exception as e:
        logger.error(f"ANALYST - Error detecting contradictions: {e}")
        contradictions = []
        state["contradictions"] = []
    
    # Compare incidents using injected tool
    try:
        related_incidents = evidence_tool.compare_incidents(document_results)
        state["related_incidents"] = related_incidents
        logger.info(f"ANALYST - Compared incidents, found {len(related_incidents)} relationships")
    except Exception as e:
        logger.error(f"ANALYST - Error comparing incidents: {e}")
        related_incidents = []
        state["related_incidents"] = []
    
    # Generate findings
    try:
        findings = generate_findings(evidence, contradictions, related_incidents)
        state["findings"] = findings
        logger.info(f"ANALYST - Generated {len(findings)} findings")
    except Exception as e:
        logger.error(f"ANALYST - Error generating findings: {e}")
        state["findings"] = ["Error generating findings"]
    
    # Determine if evidence is sufficient using evidence tool
    try:
        investigation_plan = state.get("investigation_plan")
        from app.tools.analysis_functions import evaluate_evidence_sufficiency
        from app.tools.analysis_functions import compare_all_incidents
        
        # Get incident comparisons for sufficiency evaluation
        comparisons = compare_all_incidents(document_results)
        
        sufficiency_analysis = evaluate_evidence_sufficiency(
            document_results, comparisons, contradictions, investigation_plan
        )
        state["evidence_sufficient"] = sufficiency_analysis.is_sufficient
        state["evidence_gaps"] = sufficiency_analysis.evidence_gaps
        state["evidence_sufficiency_assessment"] = sufficiency_analysis  # Store full assessment
        logger.info(f"ANALYST - Evidence sufficient: {sufficiency_analysis.is_sufficient}")
        logger.info(f"ANALYST - Evidence reasoning: {sufficiency_analysis.reasoning}")
        if sufficiency_analysis.evidence_gaps:
            logger.info(f"ANALYST - Evidence gaps: {sufficiency_analysis.evidence_gaps}")
    except Exception as e:
        logger.error(f"ANALYST - Error determining evidence sufficiency: {e}")
        state["evidence_sufficient"] = False
        state["evidence_gaps"] = []
    
    # Add investigation trace entry with observability
    try:
        trace_entry = {
            "iteration": state.get("iteration_count", 0),
            "agent": "analyst",
            "action": "evidence_analysis",
            "evidence_count": len(evidence),
            "contradiction_count": len(contradictions),
            "related_incident_count": len(related_incidents),
            "evidence_sufficient": state["evidence_sufficient"],
            "evidence_gaps": state.get("evidence_gaps", []),
            "findings_count": len(state.get("findings", [])),
            "timestamp": get_timestamp(),
            "evidence_types": list(set([e.get("evidence_type", "unknown") for e in evidence])),
            "contradiction_types": list(set([c.get("contradiction_type", "unknown") for c in contradictions]))
        }
        investigation_trace = state.get("investigation_trace", [])
        investigation_trace.append(trace_entry)
        state["investigation_trace"] = investigation_trace
        logger.info(f"ANALYST - Added trace entry for iteration {state.get('iteration_count', 0)}")
    except Exception as e:
        logger.error(f"ANALYST - Error adding trace entry: {e}")
    
    logger.info("ANALYST AGENT - Completed")
    logger.info("=" * 60)
    
    return state


def convert_to_document_results(documents: List[Dict[str, Any]]) -> List[DocumentResult]:
    """
    Convert dict documents to DocumentResult objects.
    """
    document_results = []
    
    for doc in documents:
        try:
            doc_result = DocumentResult(
                document_id=doc.get("document_id", ""),
                document_type=doc.get("document_type", doc.get("type", "unknown")),
                title=doc.get("title", ""),
                service=doc.get("service", ""),
                date=doc.get("date", ""),
                version=doc.get("version", ""),
                content=doc.get("content", ""),
                relevance_score=doc.get("relevance_score", 0.0),
                metadata=doc.get("metadata", {}),
                incident_id=doc.get("incident_id", ""),
                severity=doc.get("severity", ""),
                author=doc.get("author", "")
            )
            document_results.append(doc_result)
        except Exception as e:
            logger.error(f"Error converting document to DocumentResult: {e}")
            continue
    
    return document_results


def generate_findings(
    evidence: List[Dict[str, Any]],
    contradictions: List[Dict[str, Any]],
    related_incidents: List[Dict[str, Any]]
) -> List[str]:
    """
    Generate structured findings from the analysis.
    """
    findings = []
    
    # Evidence-based findings
    if evidence:
        services = set(claim.get("metadata", {}).get("service", "") for claim in evidence if claim.get("metadata", {}).get("service"))
        if services:
            findings.append(f"Services affected: {', '.join(services)}")
        
        versions = set(claim.get("metadata", {}).get("version", "") for claim in evidence if claim.get("metadata", {}).get("version"))
        if versions:
            findings.append(f"Versions involved: {', '.join(versions)}")
        
        incident_count = len([claim for claim in evidence if claim.get("evidence_type") == "symptom"])
        if incident_count > 0:
            findings.append(f"Incident claims found: {incident_count}")
    
    # Contradiction findings
    if contradictions:
        findings.append(f"[WARNING] Found {len(contradictions)} contradictions")
        for contradiction in contradictions[:3]:  # Limit to first 3
            contr_type = contradiction.get("contradiction_type", "unknown")
            contr_desc = contradiction.get("description", "unknown")
            resolution = contradiction.get("resolution", "")
            findings.append(f"  - {contr_type}: {contr_desc}")
            if resolution:
                findings.append(f"    Resolution: {resolution}")
    else:
        findings.append("[OK] No contradictions detected")
    
    # Incident relationship findings
    if related_incidents:
        same_count = len([r for r in related_incidents if r.get("classification") == "SAME"])
        similar_count = len([r for r in related_incidents if r.get("classification") == "SIMILAR"])
        different_count = len([r for r in related_incidents if r.get("classification") == "DIFFERENT"])
        insufficient_count = len([r for r in related_incidents if r.get("classification") == "INSUFFICIENT_EVIDENCE"])
        
        if same_count > 0:
            findings.append(f"Found {same_count} identical incident pairs")
        if similar_count > 0:
            findings.append(f"Found {similar_count} similar incident pairs")
        if different_count > 0:
            findings.append(f"Found {different_count} different incident pairs")
        if insufficient_count > 0:
            findings.append(f"Found {insufficient_count} incident pairs with insufficient evidence")
    
    return findings