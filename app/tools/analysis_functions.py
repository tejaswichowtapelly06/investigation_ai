"""
Analysis functions for evidence analysis.
These functions implement the core analysis logic for the Evidence Analyst Agent.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.tools.analysis_models import (
    EvidenceClaim, EvidenceType, Classification, CausationType,
    IncidentAttributes, IncidentComparison, Contradiction,
    CausationAnalysis, EvidenceSufficiency, EvidenceGrade,
    ContradictionType, TimelineEvent
)
from app.tools.interfaces import DocumentResult

logger = logging.getLogger(__name__)


def extract_incident_attributes(document: DocumentResult) -> IncidentAttributes:
    """
    Extract structured attributes from an incident document.
    """
    attributes = IncidentAttributes()
    
    # Extract basic fields
    attributes.service = document.service
    attributes.version = document.version
    attributes.date = document.date
    attributes.incident_id = document.incident_id
    
    # Extract from content using simple pattern matching
    content_lower = document.content.lower()
    
    # Extract symptom
    symptom_keywords = ['slow', 'down', 'outage', 'crash', 'error', 'fail', 'timeout', 'latency', 'unavailable']
    for keyword in symptom_keywords:
        if keyword in content_lower:
            if not attributes.symptom:
                attributes.symptom = keyword
            elif keyword not in attributes.symptom:
                attributes.symptom += f", {keyword}"
    
    # Extract cause
    if 'root cause' in content_lower:
        sentences = document.content.split('.')
        for sentence in sentences:
            if 'root cause' in sentence.lower():
                attributes.cause = sentence.strip()
                break
    
    # Extract failure type
    failure_types = ['database', 'network', 'memory', 'disk', 'api', 'dependency', 'configuration']
    for failure_type in failure_types:
        if failure_type in content_lower:
            if not attributes.failure_type:
                attributes.failure_type = failure_type
    
    # Extract environment
    environments = ['production', 'prod', 'staging', 'development', 'dev', 'test']
    for env in environments:
        if env in content_lower:
            attributes.environment = env
            break
    
    # Extract deployment context
    if 'deployment' in content_lower or 'deploy' in content_lower:
        attributes.deployment_context = "deployment-related"
    
    # Extract timeline information
    if 'timeline' in content_lower or 'started' in content_lower or 'occurred' in content_lower:
        sentences = document.content.split('.')
        for sentence in sentences:
            if any(word in sentence.lower() for word in ['timeline', 'started', 'occurred', 'began']):
                if not attributes.timeline:
                    attributes.timeline = sentence.strip()
                    break
    
    return attributes


def compare_incidents(
    current_attributes: IncidentAttributes,
    candidate_attributes: IncidentAttributes
) -> IncidentComparison:
    """
    Compare two incidents using multiple attributes.
    Returns a structured comparison with classification.
    """
    logger.info(f"COMPARING INCIDENTS - {current_attributes.incident_id} vs {candidate_attributes.incident_id}")
    
    matching_attributes = []
    differing_attributes = []
    
    # Compare service
    service_match = current_attributes.service.lower() == candidate_attributes.service.lower()
    if service_match:
        matching_attributes.append("service")
    else:
        differing_attributes.append("service")
    
    # Compare version
    version_match = current_attributes.version == candidate_attributes.version
    if version_match:
        matching_attributes.append("version")
    else:
        differing_attributes.append("version")
    
    # Compare symptom
    symptom_match = current_attributes.symptom.lower() == candidate_attributes.symptom.lower()
    if symptom_match:
        matching_attributes.append("symptom")
    else:
        differing_attributes.append("symptom")
    
    # Compare cause
    cause_match = current_attributes.cause.lower() == candidate_attributes.cause.lower()
    if cause_match:
        matching_attributes.append("cause")
    else:
        differing_attributes.append("cause")
    
    # Compare failure type
    failure_match = current_attributes.failure_type.lower() == candidate_attributes.failure_type.lower()
    if failure_match:
        matching_attributes.append("failure_type")
    else:
        differing_attributes.append("failure_type")
    
    # Determine classification
    classification, reasoning, confidence = determine_classification(
        current_attributes, candidate_attributes, 
        matching_attributes, differing_attributes
    )
    
    comparison = IncidentComparison(
        current_incident_id=current_attributes.incident_id,
        candidate_incident_id=candidate_attributes.incident_id,
        classification=classification,
        matching_attributes=matching_attributes,
        differing_attributes=differing_attributes,
        reasoning=reasoning,
        confidence=confidence
    )
    
    logger.info(f"COMPARISON RESULT - {classification.value} - {reasoning}")
    
    return comparison


def determine_classification(
    current: IncidentAttributes,
    candidate: IncidentAttributes,
    matching: List[str],
    differing: List[str]
) -> tuple[Classification, str, float]:
    """
    Determine the classification based on attribute comparison.
    """
    # Check for SAME incident
    if current.incident_id and candidate.incident_id:
        if current.incident_id == candidate.incident_id:
            return Classification.SAME, "Same incident ID detected", 1.0
    
    # Check for INSUFFICIENT_EVIDENCE cases first
    # Case: Both incidents have unknown/empty critical attributes
    has_meaningful_service = current.service and current.service != "unknown-service"
    has_meaningful_symptom = current.symptom and current.symptom != "unknown"
    has_meaningful_cause = current.cause and current.cause != "unknown"
    
    if not (has_meaningful_service or has_meaningful_symptom or has_meaningful_cause):
        return Classification.INSUFFICIENT_EVIDENCE, "Insufficient meaningful attributes for comparison", 0.5
    
    # Check for DIFFERENT incidents
    if not matching and differing:
        return Classification.DIFFERENT, "No matching attributes, multiple differences", 0.9
    
    # Check for DIFFERENT based on critical attributes
    if "service" in differing:
        return Classification.DIFFERENT, "Different services involved", 0.95
    
    if "cause" in differing and current.cause and candidate.cause:
        return Classification.DIFFERENT, "Different documented root causes", 0.9
    
    # Check for SIMILAR incidents
    if len(matching) >= 2 and len(differing) <= 2:
        reasoning = f"Multiple matching attributes ({', '.join(matching)}) with minor differences"
        return Classification.SIMILAR, reasoning, 0.8
    
    # Check for INSUFFICIENT_EVIDENCE
    if len(matching) == 1 and len(differing) == 1:
        return Classification.INSUFFICIENT_EVIDENCE, "Single matching and differing attribute - insufficient evidence", 0.6
    
    if not matching and not differing:
        return Classification.INSUFFICIENT_EVIDENCE, "No comparable attributes found", 0.5
    
    # Default to DIFFERENT if in doubt
    return Classification.DIFFERENT, "Insufficient similarity to classify as SAME or SIMILAR", 0.7


def detect_contradictions(documents: List[DocumentResult]) -> List[Contradiction]:
    """
    Detect contradictions between documents.
    """
    logger.info(f"DETECTING CONTRADICTIONS - Analyzing {len(documents)} documents")
    
    contradictions = []
    
    # Check for version conflicts
    version_info = {}
    for doc in documents:
        if doc.version and doc.service:
            key = f"{doc.service}:{doc.version}"
            if key in version_info:
                existing = version_info[key]
                if existing["date"] != doc.date:
                    contradictions.append(Contradiction(
                        contradiction_id=f"version_conflict_{doc.service}_{doc.version}",
                        claim_a=f"Version {doc.version} dated {existing['date']}",
                        source_a=existing["doc_id"],
                        claim_b=f"Version {doc.version} dated {doc.date}",
                        source_b=doc.document_id,
                        contradiction_type=ContradictionType.VERSION_CONFLICT,
                        description=f"Conflicting version information for {doc.service} {doc.version}",
                        documents=[existing["doc_id"], doc.document_id],
                        conflicting_claims=[
                            f"Version {doc.version} dated {existing['date']}",
                            f"Version {doc.version} dated {doc.date}"
                        ],
                        dates=[existing["date"], doc.date],
                        versions=[doc.version],
                        resolution=None,
                        confidence=0.9,
                        metadata={"service": doc.service, "version": doc.version}
                    ))
            else:
                version_info[key] = {"date": doc.date, "doc_id": doc.document_id}
    
    # Check for conflicting root causes
    root_causes = {}
    for doc in documents:
        if doc.incident_id:
            content_lower = doc.content.lower()
            if "root cause" in content_lower:
                sentences = doc.content.split('.')
                for sentence in sentences:
                    if "root cause" in sentence.lower():
                        if doc.incident_id in root_causes:
                            if root_causes[doc.incident_id] != sentence.strip():
                                contradictions.append(Contradiction(
                                    contradiction_id=f"root_cause_conflict_{doc.incident_id}",
                                    claim_a=root_causes[doc.incident_id],
                                    source_a=doc.document_id,
                                    claim_b=sentence.strip(),
                                    source_b=doc.document_id,
                                    contradiction_type=ContradictionType.ROOT_CAUSE_CONFLICT,
                                    description=f"Conflicting root causes for incident {doc.incident_id}",
                                    documents=[doc.document_id],
                                    conflicting_claims=[root_causes[doc.incident_id], sentence.strip()],
                                    resolution=None,
                                    confidence=0.85,
                                    metadata={"incident_id": doc.incident_id}
                                ))
                        else:
                            root_causes[doc.incident_id] = sentence.strip()
    
    # Check for chronological inconsistencies
    docs_with_dates = [doc for doc in documents if doc.date]
    docs_with_dates.sort(key=lambda x: x.date)
    
    for i in range(len(docs_with_dates) - 1):
        current = docs_with_dates[i]
        next_doc = docs_with_dates[i + 1]
        
        current_content = current.content.lower()
        next_content = next_doc.content.lower()
        
        # Check if resolution is mentioned before incident
        if "resolution" in current_content and "incident" in next_content:
            contradictions.append(Contradiction(
                contradiction_id=f"chronological_conflict_{current.document_id}_{next_doc.document_id}",
                claim_a=f"Resolution in {current.document_id}",
                source_a=current.document_id,
                claim_b=f"Incident in {next_doc.document_id}",
                source_b=next_doc.document_id,
                contradiction_type=ContradictionType.DATE_CONFLICT,
                description="Resolution mentioned before incident description",
                documents=[current.document_id, next_doc.document_id],
                conflicting_claims=[
                    f"Resolution in {current.document_id}",
                    f"Incident in {next_doc.document_id}"
                ],
                dates=[current.date, next_doc.date],
                resolution=None,
                confidence=0.8,
                metadata={"date_order": f"{current.date} -> {next_doc.date}"}
            ))
    
    # Check for troubleshooting guide conflicts
    troubleshooting_docs = [doc for doc in documents if doc.document_type == "troubleshooting_guide"]
    if len(troubleshooting_docs) > 1:
        for i in range(len(troubleshooting_docs)):
            for j in range(i + 1, len(troubleshooting_docs)):
                doc1 = troubleshooting_docs[i]
                doc2 = troubleshooting_docs[j]
                
                # Compare content for conflicting instructions
                if detect_guide_conflicts(doc1.content, doc2.content):
                    # Identify newer guide
                    newer_guide = doc1 if doc1.date > doc2.date else doc2
                    contradictions.append(Contradiction(
                        contradiction_id=f"guidance_conflict_{doc1.document_id}_{doc2.document_id}",
                        claim_a=f"Guidance in {doc1.document_id}",
                        source_a=doc1.document_id,
                        claim_b=f"Guidance in {doc2.document_id}",
                        source_b=doc2.document_id,
                        contradiction_type=ContradictionType.GUIDANCE_CONFLICT,
                        description=f"Conflicting troubleshooting guidance",
                        documents=[doc1.document_id, doc2.document_id],
                        conflicting_claims=[
                            f"Guidance in {doc1.document_id}",
                            f"Guidance in {doc2.document_id}"
                        ],
                        resolution=f"Prefer newer guide: {newer_guide.document_id}",
                        confidence=0.75,
                        metadata={"newer_guide": newer_guide.document_id}
                    ))
    
    logger.info(f"CONTRADICTIONS DETECTED - {len(contradictions)}")
    
    return contradictions


def detect_guide_conflicts(content1: str, content2: str) -> bool:
    """
    Detect if two troubleshooting guides have conflicting instructions.
    """
    # Simple keyword-based conflict detection
    conflict_keywords = ['should', 'must', 'never', 'always', 'avoid', 'use', 'do not']
    
    # Extract instructions from both guides
    instructions1 = extract_instructions(content1)
    instructions2 = extract_instructions(content2)
    
    # Check for direct contradictions
    for inst1 in instructions1:
        for inst2 in instructions2:
            if are_contradictory(inst1, inst2):
                return True
    
    return False


def extract_instructions(content: str) -> List[str]:
    """
    Extract instructional statements from content.
    """
    instructions = []
    sentences = content.split('.')
    
    for sentence in sentences:
        sentence_lower = sentence.lower().strip()
        if any(keyword in sentence_lower for keyword in ['should', 'must', 'never', 'always', 'avoid']):
            if len(sentence_lower) > 10:  # Filter very short sentences
                instructions.append(sentence.strip())
    
    return instructions


def are_contradictory(inst1: str, inst2: str) -> bool:
    """
    Check if two instructions are contradictory.
    """
    inst1_lower = inst1.lower()
    inst2_lower = inst2.lower()
    
    # Check for opposite instructions
    contradictions = [
        ('should', 'should not'),
        ('must', 'must not'),
        ('always', 'never'),
        ('use', 'avoid'),
        ('do', 'do not')
    ]
    
    for pos, neg in contradictions:
        if pos in inst1_lower and neg in inst2_lower:
            return True
        if neg in inst1_lower and pos in inst2_lower:
            return True
    
    return False


def check_temporal_consistency(deployment: DocumentResult, incident: DocumentResult) -> CausationAnalysis:
    """
    Check temporal consistency between deployment and incident.
    Distinguishes between temporal association and documented causation.
    """
    logger.info(f"CHECKING TEMPORAL CONSISTENCY - Deployment: {deployment.document_id}, Incident: {incident.document_id}")
    
    deployment_date = deployment.date
    incident_date = incident.date
    
    if not deployment_date or not incident_date:
        return CausationAnalysis(
            deployment_id=deployment.document_id,
            incident_id=incident.incident_id,
            causation_type=CausationType.INSUFFICIENT_EVIDENCE,
            temporal_relationship="Unable to determine - missing date information",
            documented_evidence=[],
            reasoning="Missing date information for temporal analysis",
            confidence=0.3
        )
    
    try:
        dep_dt = datetime.strptime(deployment_date, "%Y-%m-%d")
        inc_dt = datetime.strptime(incident_date, "%Y-%m-%d")
        
        time_diff = (inc_dt - dep_dt).days
        
        if time_diff < 0:
            temporal_relationship = f"Incident occurred {abs(time_diff)} days BEFORE deployment"
            causation_type = CausationType.NO_EVIDENCE
            confidence = 0.9
        elif time_diff == 0:
            temporal_relationship = "Incident occurred on same day as deployment"
            causation_type = CausationType.TEMPORAL_ASSOCIATION
            confidence = 0.7
        elif time_diff <= 1:
            temporal_relationship = f"Incident occurred {time_diff} day(s) after deployment"
            causation_type = CausationType.TEMPORAL_ASSOCIATION
            confidence = 0.8
        elif time_diff <= 7:
            temporal_relationship = f"Incident occurred {time_diff} days after deployment"
            causation_type = CausationType.TEMPORAL_ASSOCIATION
            confidence = 0.6
        else:
            temporal_relationship = f"Incident occurred {time_diff} days after deployment - unlikely causal relationship"
            causation_type = CausationType.NO_EVIDENCE
            confidence = 0.8
        
        # Check for documented causal evidence
        documented_evidence = []
        deployment_content_lower = deployment.content.lower()
        incident_content_lower = incident.content.lower()
        
        if "caused" in deployment_content_lower or "caused" in incident_content_lower:
            documented_evidence.append("Document mentions causation")
            causation_type = CausationType.DOCUMENTED_CAUSAL
            confidence = 0.9
        
        if "related" in deployment_content_lower or "related" in incident_content_lower:
            documented_evidence.append("Document mentions relationship")
        
        reasoning = f"Temporal relationship: {temporal_relationship}. "
        if causation_type == CausationType.DOCUMENTED_CAUSAL:
            reasoning += "Documented causal evidence found."
        elif causation_type == CausationType.TEMPORAL_ASSOCIATION:
            reasoning += "Temporal association only - no documented causation."
        else:
            reasoning += "No evidence of causal relationship."
        
        return CausationAnalysis(
            deployment_id=deployment.document_id,
            incident_id=incident.incident_id,
            causation_type=causation_type,
            temporal_relationship=temporal_relationship,
            documented_evidence=documented_evidence,
            reasoning=reasoning,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Error parsing dates: {e}")
        return CausationAnalysis(
            deployment_id=deployment.document_id,
            incident_id=incident.incident_id,
            causation_type=CausationType.INSUFFICIENT_EVIDENCE,
            temporal_relationship="Error parsing dates",
            documented_evidence=[],
            reasoning=f"Error in temporal analysis: {e}",
            confidence=0.2
        )


def check_version_consistency(documents: List[DocumentResult]) -> List[Contradiction]:
    """
    Check for version consistency across documents.
    """
    logger.info(f"CHECKING VERSION CONSISTENCY - Analyzing {len(documents)} documents")
    
    contradictions = []
    
    # Group documents by service and version
    service_version_docs = {}
    for doc in documents:
        if doc.service and doc.version:
            key = f"{doc.service}:{doc.version}"
            if key not in service_version_docs:
                service_version_docs[key] = []
            service_version_docs[key].append(doc)
    
    # Check for contradictions within same service/version
    for key, docs in service_version_docs.items():
        if len(docs) > 1:
            # Check for conflicting information
            incident_ids = set(doc.incident_id for doc in docs if doc.incident_id)
            if len(incident_ids) > 1:
                contradictions.append(Contradiction(
                    contradiction_type="version_incident_conflict",
                    description=f"Multiple incidents associated with {key}",
                    documents=[doc.document_id for doc in docs],
                    conflicting_claims=[f"Incident {inc_id}" for inc_id in incident_ids],
                    resolution=None,
                    confidence=0.85,
                    metadata={"service_version": key, "incident_count": len(incident_ids)}
                ))
    
    logger.info(f"VERSION CONTRADICTIONS - {len(contradictions)}")
    
    return contradictions


def grade_evidence(claim: EvidenceClaim, all_claims: List[EvidenceClaim], documents: List[DocumentResult]) -> EvidenceGrade:
    """
    Grade evidence based on multiple factors:
    - Direct vs inferred evidence
    - Corroboration from multiple sources
    - Contradictory evidence
    - Version/time applicability
    """
    # Count supporting claims (corroboration)
    supporting_claims = [c for c in all_claims if claim.claim in c.supports]
    
    # Count contradictory claims
    contradictory_claims = [c for c in all_claims if claim.claim in c.contradicts]
    
    # Check if claim is directly stated in document
    source_doc = next((d for d in documents if d.document_id == claim.source_document_id), None)
    is_direct = False
    if source_doc:
        # Direct evidence if claim text appears verbatim or with minor variations
        content_lower = source_doc.content.lower()
        claim_words = claim.claim.lower().split()[:5]  # Check first 5 words
        if len(claim_words) >= 3:
            phrase = " ".join(claim_words)
            is_direct = phrase in content_lower
    
    # Determine grade
    if contradictory_claims:
        return EvidenceGrade.CONTRADICTED
    elif is_direct and len(supporting_claims) >= 2:
        return EvidenceGrade.CORROBORATED
    elif is_direct:
        return EvidenceGrade.DIRECT_EVIDENCE
    elif len(supporting_claims) >= 2:
        return EvidenceGrade.CORROBORATED
    elif len(supporting_claims) >= 1:
        return EvidenceGrade.INFERRED
    else:
        return EvidenceGrade.UNKNOWN


def extract_evidence_claims(documents: List[DocumentResult]) -> List[EvidenceClaim]:
    """
    Extract structured evidence claims from documents with grading.
    """
    claims = []
    
    for doc in documents:
        # Extract various types of claims
        content_lower = doc.content.lower()
        
        # Symptom claims
        symptom_keywords = ['slow', 'down', 'outage', 'crash', 'error', 'fail', 'timeout', 'latency', 'unavailable']
        for keyword in symptom_keywords:
            if keyword in content_lower:
                claim = EvidenceClaim(
                    evidence_id=f"{doc.document_id}_symptom_{keyword}",
                    claim=f"Symptom: {keyword}",
                    source_document_id=doc.document_id,
                    source_document_type=doc.document_type,
                    source_date=doc.date,
                    relevant_service=doc.service,
                    relevant_version=doc.version,
                    related_entity=doc.incident_id,
                    evidence_type=EvidenceType.SYMPTOM,
                    grade=EvidenceGrade.UNKNOWN,
                    supporting_text=doc.content[:200],
                    metadata={"keyword": keyword}
                )
                claims.append(claim)
        
        # Root cause claims
        if 'root cause' in content_lower:
            sentences = doc.content.split('.')
            for sentence in sentences:
                if 'root cause' in sentence.lower():
                    claim = EvidenceClaim(
                        evidence_id=f"{doc.document_id}_root_cause",
                        claim=sentence.strip(),
                        source_document_id=doc.document_id,
                        source_document_type=doc.document_type,
                        source_date=doc.date,
                        relevant_service=doc.service,
                        relevant_version=doc.version,
                        related_entity=doc.incident_id,
                        evidence_type=EvidenceType.ROOT_CAUSE,
                        grade=EvidenceGrade.UNKNOWN,
                        supporting_text=sentence.strip(),
                        metadata={"incident_id": doc.incident_id}
                    )
                    claims.append(claim)
                    break
        
        # Deployment claims
        if 'deployment' in content_lower or 'deploy' in content_lower:
            claim = EvidenceClaim(
                evidence_id=f"{doc.document_id}_deployment",
                claim="Deployment-related event",
                source_document_id=doc.document_id,
                source_document_type=doc.document_type,
                source_date=doc.date,
                relevant_service=doc.service,
                relevant_version=doc.version,
                related_entity=doc.incident_id,
                evidence_type=EvidenceType.DEPLOYMENT,
                grade=EvidenceGrade.UNKNOWN,
                supporting_text=doc.content[:200],
                metadata={"deployment_context": True}
            )
            claims.append(claim)
        
        # Version claims
        if doc.version:
            claim = EvidenceClaim(
                evidence_id=f"{doc.document_id}_version",
                claim=f"Version: {doc.version}",
                source_document_id=doc.document_id,
                source_document_type=doc.document_type,
                source_date=doc.date,
                relevant_service=doc.service,
                relevant_version=doc.version,
                related_entity=doc.incident_id,
                evidence_type=EvidenceType.VERSION,
                grade=EvidenceGrade.DIRECT_EVIDENCE,
                supporting_text=f"Document mentions version {doc.version}",
                metadata={"version": doc.version}
            )
            claims.append(claim)
    
    # Grade all claims
    for claim in claims:
        claim.grade = grade_evidence(claim, claims, documents)
    
    logger.info(f"EVIDENCE CLAIMS EXTRACTED - {len(claims)} claims")
    
    return claims


def compare_all_incidents(documents: List[DocumentResult]) -> List[IncidentComparison]:
    """
    Compare all incident documents against each other.
    """
    logger.info(f"COMPARING ALL INCIDENTS - {len(documents)} documents")
    
    # Extract incident attributes from documents
    incident_docs = [doc for doc in documents if doc.incident_id]
    attributes_list = [extract_incident_attributes(doc) for doc in incident_docs]
    
    comparisons = []
    
    # Compare each incident with every other incident
    for i in range(len(attributes_list)):
        for j in range(i + 1, len(attributes_list)):
            comparison = compare_incidents(attributes_list[i], attributes_list[j])
            comparisons.append(comparison)
    
    logger.info(f"INCIDENT COMPARISONS COMPLETE - {len(comparisons)} comparisons")
    
    return comparisons


def evaluate_evidence_sufficiency(
    documents: List[DocumentResult],
    comparisons: List[IncidentComparison],
    contradictions: List[Contradiction],
    investigation_plan: Any
) -> EvidenceSufficiency:
    """
    Evaluate whether the gathered evidence is sufficient to answer the investigation question.
    """
    logger.info("EVALUATING EVIDENCE SUFFICIENCY")
    
    # Determine required evidence types based on investigation plan
    required_types = []
    available_types = []
    evidence_gaps = []
    
    # Check for basic evidence types
    has_incident_reports = any(doc.document_type == "incident_report" for doc in documents)
    has_postmortems = any(doc.document_type == "postmortem" for doc in documents)
    has_deployment_info = any(doc.document_type == "deployment_note" for doc in documents)
    has_troubleshooting_guides = any(doc.document_type == "troubleshooting_guide" for doc in documents)
    
    if has_incident_reports:
        available_types.append(EvidenceType.SYMPTOM)
        available_types.append(EvidenceType.FAILURE_TYPE)
    
    if has_postmortems:
        available_types.append(EvidenceType.ROOT_CAUSE)
        available_types.append(EvidenceType.RESOLUTION)
    
    if has_deployment_info:
        available_types.append(EvidenceType.DEPLOYMENT)
        available_types.append(EvidenceType.VERSION)
    
    if has_troubleshooting_guides:
        available_types.append(EvidenceType.ENVIRONMENT)
    
    # Default required types
    required_types = [EvidenceType.SYMPTOM, EvidenceType.ROOT_CAUSE]
    
    # Check for gaps
    for req_type in required_types:
        if req_type not in available_types:
            evidence_gaps.append(f"Missing {req_type.value} evidence")
    
    # Check for contradictions
    if contradictions:
        evidence_gaps.append(f"Contradictions detected ({len(contradictions)})")
    
    # Check for INSUFFICIENT_EVIDENCE classifications
    insufficient_comparisons = [c for c in comparisons if c.classification == Classification.INSUFFICIENT_EVIDENCE]
    if insufficient_comparisons:
        evidence_gaps.append(f"Insufficient evidence for incident comparisons ({len(insufficient_comparisons)})")
    
    # Determine sufficiency
    is_sufficient = len(evidence_gaps) == 0 and len(documents) >= 2
    
    # Calculate confidence
    confidence = 0.8 if is_sufficient else 0.4
    if len(evidence_gaps) == 1:
        confidence = 0.6
    
    reasoning = f"Evidence evaluation: {len(documents)} documents, {len(available_types)} evidence types available."
    if evidence_gaps:
        reasoning += f" Gaps: {', '.join(evidence_gaps)}."
    else:
        reasoning += " No significant gaps detected."
    
    return EvidenceSufficiency(
        is_sufficient=is_sufficient,
        evidence_gaps=evidence_gaps,
        confidence=confidence,
        reasoning=reasoning,
        required_evidence_types=required_types,
        available_evidence_types=available_types
    )