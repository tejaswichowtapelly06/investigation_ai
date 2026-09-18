import logging
from typing import Dict, Any, List
from app.graph.state import InvestigationState, InvestigationPlan
from app.tools.analysis_models import (
    EvidenceClaim, EvidenceType, Classification, CausationType,
    IncidentAttributes, IncidentComparison, Contradiction,
    CausationAnalysis, EvidenceSufficiency
)
from app.tools.analysis_functions import (
    extract_incident_attributes, compare_incidents, detect_contradictions,
    check_temporal_consistency, check_version_consistency, evaluate_evidence_sufficiency
)
from app.tools.interfaces import DocumentResult
from datetime import datetime

logger = logging.getLogger(__name__)


def get_timestamp() -> str:
    """Get current timestamp for logging."""
    return datetime.now().isoformat()


def analyst_agent(state: InvestigationState) -> InvestigationState:
    """
    Evidence Analyst Agent: Analyzes retrieved documents, compares incidents,
    detects contradictions, and determines if evidence is sufficient.
    Uses structured analysis models and deterministic logic.
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
        
        logger.info("ANALYST AGENT - Completed (no documents)")
        logger.info("=" * 60)
        return state
    
    # Convert dict documents to DocumentResult objects
    document_results = convert_to_document_results(retrieved_documents)
    
    # Extract evidence claims from documents
    try:
        evidence_claims = extract_evidence_claims(document_results)
        state["evidence"] = [claim.model_dump() for claim in evidence_claims]
        logger.info(f"ANALYST - Extracted {len(evidence_claims)} evidence claims")
    except Exception as e:
        logger.error(f"ANALYST - Error extracting evidence claims: {e}")
        evidence_claims = []
        state["evidence"] = []
    
    # Detect contradictions
    try:
        contradictions = detect_contradictions(document_results)
        state["contradictions"] = [contr.model_dump() for contr in contradictions]
        logger.info(f"ANALYST - Found {len(contradictions)} contradictions")
    except Exception as e:
        logger.error(f"ANALYST - Error detecting contradictions: {e}")
        contradictions = []
        state["contradictions"] = []
    
    # Compare incidents
    try:
        related_incidents = compare_all_incidents(document_results)
        state["related_incidents"] = [rel.model_dump() for rel in related_incidents]
        logger.info(f"ANALYST - Compared incidents, found {len(related_incidents)} relationships")
    except Exception as e:
        logger.error(f"ANALYST - Error comparing incidents: {e}")
        related_incidents = []
        state["related_incidents"] = []
    
    # Check version consistency
    try:
        version_contradictions = check_version_consistency(document_results)
        if version_contradictions:
            all_contradictions = contradictions + version_contradictions
            state["contradictions"] = [contr.model_dump() for contr in all_contradictions]
            logger.info(f"ANALYST - Found {len(version_contradictions)} version contradictions")
    except Exception as e:
        logger.error(f"ANALYST - Error checking version consistency: {e}")
    
    # Generate findings
    try:
        findings = generate_findings(evidence_claims, contradictions, related_incidents)
        state["findings"] = findings
        logger.info(f"ANALYST - Generated {len(findings)} findings")
    except Exception as e:
        logger.error(f"ANALYST - Error generating findings: {e}")
        state["findings"] = ["Error generating findings"]
    
    # Determine if evidence is sufficient
    try:
        investigation_plan = state.get("investigation_plan")
        sufficiency_analysis = evaluate_evidence_sufficiency(
            document_results, related_incidents, contradictions, investigation_plan
        )
        state["evidence_sufficient"] = sufficiency_analysis.is_sufficient
        state["evidence_gaps"] = sufficiency_analysis.evidence_gaps
        logger.info(f"ANALYST - Evidence sufficient: {sufficiency_analysis.is_sufficient}")
        logger.info(f"ANALYST - Evidence reasoning: {sufficiency_analysis.reasoning}")
        if sufficiency_analysis.evidence_gaps:
            logger.info(f"ANALYST - Evidence gaps: {sufficiency_analysis.evidence_gaps}")
    except Exception as e:
        logger.error(f"ANALYST - Error determining evidence sufficiency: {e}")
        state["evidence_sufficient"] = False
        state["evidence_gaps"] = []
    
    # Add investigation trace entry
    try:
        trace_entry = {
            "iteration": state.get("iteration_count", 0),
            "agent": "analyst",
            "action": "evidence_analysis",
            "evidence_count": len(evidence_claims),
            "contradiction_count": len(contradictions),
            "related_incident_count": len(related_incidents),
            "evidence_sufficient": state["evidence_sufficient"],
            "evidence_gaps": state.get("evidence_gaps", []),
            "findings_count": len(state.get("findings", [])),
            "timestamp": get_timestamp()
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


def extract_evidence_claims(documents: List[DocumentResult]) -> List[EvidenceClaim]:
    """
    Extract structured evidence claims from documents.
    """
    claims = []
    
    for doc in documents:
        # Extract symptom claim
        if doc.service:
            claims.append(EvidenceClaim(
                claim=f"Service {doc.service} affected",
                document_id=doc.document_id,
                evidence_type=EvidenceType.SERVICE,
                confidence=0.9,
                metadata={"service": doc.service}
            ))
        
        # Extract version claim
        if doc.version:
            claims.append(EvidenceClaim(
                claim=f"Version {doc.version} involved",
                document_id=doc.document_id,
                evidence_type=EvidenceType.VERSION,
                confidence=0.85,
                metadata={"version": doc.version}
            ))
        
        # Extract incident claim
        if doc.incident_id:
            claims.append(EvidenceClaim(
                claim=f"Incident {doc.incident_id} documented",
                document_id=doc.document_id,
                evidence_type=EvidenceType.SYMPTOM,
                confidence=0.95,
                metadata={"incident_id": doc.incident_id}
            ))
        
        # Extract cause claim
        content_lower = doc.content.lower()
        if "root cause" in content_lower:
            sentences = doc.content.split('.')
            for sentence in sentences:
                if "root cause" in sentence.lower():
                    claims.append(EvidenceClaim(
                        claim=sentence.strip(),
                        document_id=doc.document_id,
                        evidence_type=EvidenceType.ROOT_CAUSE,
                        confidence=0.8,
                        metadata={"context": "root cause extraction"}
                    ))
                    break
    
    return claims


def compare_all_incidents(documents: List[DocumentResult]) -> List[IncidentComparison]:
    """
    Compare all incident documents to find relationships.
    """
    related_incidents = []
    
    # Filter only incident documents
    incident_docs = [doc for doc in documents if doc.document_type == "incident_report"]
    
    logger.info(f"ANALYST - Comparing {len(incident_docs)} incident documents")
    
    # Extract attributes for each incident
    incident_attributes = {}
    for doc in incident_docs:
        attributes = extract_incident_attributes(doc)
        incident_attributes[doc.document_id] = attributes
    
    # Compare each pair of incidents
    for i in range(len(incident_docs)):
        for j in range(i + 1, len(incident_docs)):
            doc1 = incident_docs[i]
            doc2 = incident_docs[j]
            
            attrs1 = incident_attributes[doc1.document_id]
            attrs2 = incident_attributes[doc2.document_id]
            
            comparison = compare_incidents(attrs1, attrs2)
            related_incidents.append(comparison)
    
    return related_incidents


def generate_findings(
    evidence_claims: List[EvidenceClaim],
    contradictions: List[Contradiction],
    related_incidents: List[IncidentComparison]
) -> List[str]:
    """
    Generate structured findings from the analysis.
    """
    findings = []
    
    # Evidence-based findings
    if evidence_claims:
        services = set(claim.metadata.get("service", "") for claim in evidence_claims if claim.metadata.get("service"))
        if services:
            findings.append(f"Services affected: {', '.join(services)}")
        
        versions = set(claim.metadata.get("version", "") for claim in evidence_claims if claim.metadata.get("version"))
        if versions:
            findings.append(f"Versions involved: {', '.join(versions)}")
        
        incident_count = len([claim for claim in evidence_claims if claim.evidence_type == EvidenceType.SYMPTOM])
        if incident_count > 0:
            findings.append(f"Incident claims found: {incident_count}")
    
    # Contradiction findings
    if contradictions:
        findings.append(f"[WARNING] Found {len(contradictions)} contradictions")
        for contradiction in contradictions[:3]:  # Limit to first 3
            findings.append(f"  - {contradiction.contradiction_type}: {contradiction.description}")
            if contradiction.resolution:
                findings.append(f"    Resolution: {contradiction.resolution}")
    else:
        findings.append("[OK] No contradictions detected")
    
    # Incident relationship findings
    if related_incidents:
        same_count = len([r for r in related_incidents if r.classification == Classification.SAME])
        similar_count = len([r for r in related_incidents if r.classification == Classification.SIMILAR])
        different_count = len([r for r in related_incidents if r.classification == Classification.DIFFERENT])
        insufficient_count = len([r for r in related_incidents if r.classification == Classification.INSUFFICIENT_EVIDENCE])
        
        if same_count > 0:
            findings.append(f"Found {same_count} identical incident pairs")
        if similar_count > 0:
            findings.append(f"Found {similar_count} similar incident pairs")
        if different_count > 0:
            findings.append(f"Found {different_count} different incident pairs")
        if insufficient_count > 0:
            findings.append(f"Found {insufficient_count} incident pairs with insufficient evidence")
    
    return findings