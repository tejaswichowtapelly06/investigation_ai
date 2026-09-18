import logging
from typing import List, Dict, Any
from app.graph.state import IncidentComparison

logger = logging.getLogger(__name__)


def compare_incidents(incident1: Dict[str, Any], incident2: Dict[str, Any]) -> IncidentComparison:
    """
    Compare two incidents to determine if they are the same, similar, different, or if there's insufficient evidence.
    """
    logger.info(f"EVIDENCE TOOL - Comparing incidents: {incident1.get('incident_id', 'unknown')} vs {incident2.get('incident_id', 'unknown')}")
    
    # Check if they have the same incident ID
    if incident1.get("incident_id") and incident2.get("incident_id"):
        if incident1["incident_id"] == incident2["incident_id"]:
            logger.info("EVIDENCE TOOL - Same incident ID detected")
            return IncidentComparison.SAME
    
    # Check service match
    service_match = (incident1.get("service", "").lower() == incident2.get("service", "").lower())
    
    # Check version match
    version_match = (incident1.get("version", "") == incident2.get("version", ""))
    
    # Check content similarity (basic keyword overlap)
    content1_words = set(incident1.get("content", "").lower().split())
    content2_words = set(incident2.get("content", "").lower().split())
    
    if content1_words and content2_words:
        overlap = len(content1_words & content2_words)
        total = len(content1_words | content2_words)
        similarity = overlap / total if total > 0 else 0
    else:
        similarity = 0
    
    logger.info(f"EVIDENCE TOOL - Service match: {service_match}, Version match: {version_match}, Content similarity: {similarity:.2f}")
    
    # Decision logic
    if service_match and version_match and similarity > 0.7:
        # High similarity but different incident IDs - could be same incident documented differently
        logger.info("EVIDENCE TOOL - Classifying as SIMILAR (high similarity)")
        return IncidentComparison.SIMILAR
    elif service_match and similarity > 0.5:
        # Same service, some content overlap
        logger.info("EVIDENCE TOOL - Classifying as SIMILAR (moderate similarity)")
        return IncidentComparison.SIMILAR
    elif not service_match:
        # Different services
        logger.info("EVIDENCE TOOL - Classifying as DIFFERENT (different services)")
        return IncidentComparison.DIFFERENT
    elif similarity < 0.3:
        # Same service but very different content
        logger.info("EVIDENCE TOOL - Classifying as DIFFERENT (low similarity)")
        return IncidentComparison.DIFFERENT
    else:
        # Not enough information to determine
        logger.info("EVIDENCE TOOL - Classifying as INSUFFICIENT_EVIDENCE")
        return IncidentComparison.INSUFFICIENT_EVIDENCE


def detect_contradictions(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect contradictions or outdated guidance in documents.
    """
    logger.info(f"EVIDENCE TOOL - Checking for contradictions in {len(documents)} documents")
    
    contradictions = []
    
    # Check for version conflicts
    version_info = {}
    for doc in documents:
        service = doc.get("service", "")
        version = doc.get("version", "")
        date = doc.get("date", "")
        
        if service and version:
            key = f"{service}:{version}"
            if key in version_info:
                if date and version_info[key]["date"] != date:
                    contradictions.append({
                        "type": "version_conflict",
                        "description": f"Conflicting version information for {service} {version}",
                        "documents": [version_info[key]["doc_id"], doc["document_id"]],
                        "details": f"Same version {version} mentioned with different dates: {version_info[key]['date']} vs {date}"
                    })
            else:
                version_info[key] = {"date": date, "doc_id": doc["document_id"]}
    
    # Check for contradictory root causes
    root_causes = {}
    for doc in documents:
        incident_id = doc.get("incident_id", "")
        content = doc.get("content", "").lower()
        
        if incident_id:
            # Look for root cause indicators
            if "root cause" in content:
                if incident_id in root_causes:
                    if root_causes[incident_id] != content:
                        contradictions.append({
                            "type": "root_cause_conflict",
                            "description": f"Conflicting root causes for incident {incident_id}",
                            "documents": [doc["document_id"]],
                            "details": f"Multiple root cause descriptions found for {incident_id}"
                        })
                else:
                    root_causes[incident_id] = content
    
    # Check for chronological inconsistencies
    docs_with_dates = [doc for doc in documents if doc.get("date")]
    docs_with_dates.sort(key=lambda x: x["date"])
    
    for i in range(len(docs_with_dates) - 1):
        current = docs_with_dates[i]
        next_doc = docs_with_dates[i + 1]
        
        # Check if resolution is mentioned before incident
        current_content = current.get("content", "").lower()
        next_content = next_doc.get("content", "").lower()
        
        if "resolution" in current_content and "incident" in next_content:
            contradictions.append({
                "type": "chronological_inconsistency",
                "description": "Resolution mentioned before incident description",
                "documents": [current["document_id"], next_doc["document_id"]],
                "details": f"Document {current['document_id']} mentions resolution but document {next_doc['document_id']} describes incident"
            })
    
    logger.info(f"EVIDENCE TOOL - Found {len(contradictions)} contradictions")
    
    return contradictions


def extract_evidence_from_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract structured evidence from retrieved documents.
    """
    logger.info(f"EVIDENCE TOOL - Extracting evidence from {len(documents)} documents")
    
    evidence = []
    
    for doc in documents:
        evidence_item = {
            "document_id": doc["document_id"],
            "source_type": doc.get("type", "unknown"),
            "service": doc.get("service", ""),
            "version": doc.get("version", ""),
            "date": doc.get("date", ""),
            "incident_id": doc.get("incident_id", ""),
            "key_points": extract_key_points(doc.get("content", "")),
            "severity": doc.get("severity", "unknown")
        }
        evidence.append(evidence_item)
    
    logger.info(f"EVIDENCE TOOL - Extracted {len(evidence)} evidence items")
    
    return evidence


def extract_key_points(content: str) -> List[str]:
    """
    Extract key points from document content.
    """
    key_points = []
    
    # Look for common patterns
    if "root cause" in content.lower():
        # Extract sentence containing "root cause"
        sentences = content.split(".")
        for sentence in sentences:
            if "root cause" in sentence.lower():
                key_points.append(f"Root cause: {sentence.strip()}")
                break
    
    if "resolution" in content.lower():
        sentences = content.split(".")
        for sentence in sentences:
            if "resolution" in sentence.lower():
                key_points.append(f"Resolution: {sentence.strip()}")
                break
    
    if "action" in content.lower():
        sentences = content.split(".")
        for sentence in sentences:
            if "action" in sentence.lower():
                key_points.append(f"Action item: {sentence.strip()}")
    
    # Extract service and version mentions
    words = content.split()
    for i, word in enumerate(words):
        if word.lower() == "service" and i + 1 < len(words):
            key_points.append(f"Service mentioned: {words[i + 1]}")
    
    return key_points