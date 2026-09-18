import logging
import re
from typing import List, Dict, Any
from datetime import datetime
from app.graph.state import InvestigationState, InvestigationPlan, Entity, EntityType, InvestigationTask, RequiredEvidence

logger = logging.getLogger(__name__)


def get_timestamp() -> str:
    """Get current timestamp for logging."""
    return datetime.now().isoformat()


def planner_agent(state: InvestigationState) -> InvestigationState:
    """
    Planner Agent: Converts natural-language question into structured investigation plan.
    The Planner reasons about what evidence is needed rather than simply summarizing the question.
    """
    logger.info("=" * 60)
    logger.info("PLANNER AGENT - Starting investigation planning")
    logger.info("=" * 60)
    logger.info(f"Question: {state['question']}")
    
    question = state["question"]
    
    # Extract entities with advanced pattern matching
    entities = extract_entities_advanced(question)
    logger.info(f"Extracted {len(entities)} entities")
    for entity in entities:
        logger.info(f"  - {entity.entity_type.value}: {entity.value} (confidence: {entity.confidence})")
    
    # Create structured investigation plan with evidence-based reasoning
    investigation_plan = create_structured_investigation_plan(question, entities)
    logger.info(f"Objective: {investigation_plan.objective}")
    logger.info(f"Required evidence items: {len(investigation_plan.required_evidence)}")
    logger.info(f"Investigation tasks: {len(investigation_plan.investigation_tasks)}")
    logger.info(f"Unanswered questions: {len(investigation_plan.unanswered_questions)}")
    logger.info(f"Reasoning: {investigation_plan.reasoning}")
    
    # Update state with structured plan
    state["investigation_plan"] = investigation_plan
    state["entities"] = entities  # Initial entities from question
    state["discovered_entities"] = entities  # Initialize with entities from question
    state["required_evidence"] = investigation_plan.required_evidence
    state["iteration_count"] = 0
    state["status"] = "researching"  # Transition to research phase
    
    # Add investigation trace entry with observability
    try:
        trace_entry = {
            "iteration": 0,
            "agent": "planner",
            "action": "investigation_planning",
            "objective": investigation_plan.objective,
            "entity_count": len(entities),
            "task_count": len(investigation_plan.investigation_tasks),
            "evidence_requirement_count": len(investigation_plan.required_evidence),
            "reasoning": investigation_plan.reasoning,
            "timestamp": get_timestamp(),
            "entities": [{"type": e.entity_type.value, "value": e.value} for e in entities]
        }
        state["investigation_trace"] = [trace_entry]
        logger.info("PLANNER - Added initial trace entry")
    except Exception as e:
        logger.error(f"PLANNER - Error adding trace entry: {e}")
        state["investigation_trace"] = []
    
    logger.info("PLANNER AGENT - Completed")
    logger.info("=" * 60)
    
    return state


def extract_entities_advanced(question: str) -> List[Entity]:
    """
    Extract entities with advanced pattern matching and entity type classification.
    """
    entities = []
    question_lower = question.lower()
    
    # Extract service names
    service_patterns = [
        r'(\w+)\s+service',
        r'(\w+)\s+api',
        r'service\s+(\w+)',
        r'api\s+(\w+)'
    ]
    for pattern in service_patterns:
        matches = re.finditer(pattern, question, re.IGNORECASE)
        for match in matches:
            service_name = match.group(1).strip()
            if len(service_name) > 2 and service_name.lower() not in ["the", "a", "an"]:
                entities.append(Entity(
                    entity_type=EntityType.SERVICE,
                    value=service_name,
                    confidence=0.9,
                    context=match.group(0)
                ))
    
    # Extract incident IDs
    incident_patterns = [
        r'incident\s*[#-]?\s*([A-Z]+\d+-\d+)',  # INC-2024-001 format
        r'inc\s*[#-]?\s*([A-Z]+\d+-\d+)',  # INC-2024-001 format
        r'#([A-Z]+\d+-\d+)',  # #INC-2024-001 format
        r'incident\s*[#-]?\s*(\w+)',  # Fallback for other formats
        r'inc\s*[#-]?\s*(\w+)'  # Fallback for other formats
    ]
    for pattern in incident_patterns:
        matches = re.finditer(pattern, question, re.IGNORECASE)
        for match in matches:
            incident_id = match.group(1).strip()
            entities.append(Entity(
                entity_type=EntityType.INCIDENT_ID,
                value=incident_id,
                confidence=0.95,
                context=match.group(0)
            ))
    
    # Extract dates
    date_patterns = [
        r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}',
        r'september\s+\d{1,2}',
        r'january\s+\d{1,2}'
    ]
    for pattern in date_patterns:
        matches = re.finditer(pattern, question, re.IGNORECASE)
        for match in matches:
            date_value = match.group(0).strip()
            entities.append(Entity(
                entity_type=EntityType.DATE,
                value=date_value,
                confidence=0.85,
                context=match.group(0)
            ))
    
    # Extract versions
    version_patterns = [
        r'v\d+\.\d+(?:\.\d+)?',
        r'version\s+\d+\.\d+(?:\.\d+)?',
        r'\d+\.\d+(?:\.\d+)?'
    ]
    for pattern in version_patterns:
        matches = re.finditer(pattern, question, re.IGNORECASE)
        for match in matches:
            version_value = match.group(0).strip()
            entities.append(Entity(
                entity_type=EntityType.VERSION,
                value=version_value,
                confidence=0.8,
                context=match.group(0)
            ))
    
    # Extract symptoms/errors
    symptom_keywords = ['slow', 'down', 'outage', 'crash', 'error', 'fail', 'timeout', 'latency', 'unavailable']
    for keyword in symptom_keywords:
        if keyword in question_lower:
            # Extract context around the symptom
            context_start = max(0, question_lower.find(keyword) - 20)
            context_end = min(len(question), question_lower.find(keyword) + len(keyword) + 20)
            context = question[context_start:context_end].strip()
            entities.append(Entity(
                entity_type=EntityType.SYMPTOM,
                value=keyword,
                confidence=0.7,
                context=context
            ))
    
    # Extract deployment mentions
    if 'deployment' in question_lower or 'deploy' in question_lower:
        deployment_pattern = r'(?:deployment|deploy)\s+(?:of|to|for)?\s*(\w+)'
        matches = re.finditer(deployment_pattern, question, re.IGNORECASE)
        for match in matches:
            deployment_value = match.group(1).strip() if match.group(1) else "deployment"
            entities.append(Entity(
                entity_type=EntityType.DEPLOYMENT,
                value=deployment_value,
                confidence=0.8,
                context=match.group(0)
            ))
    
    # Extract document types
    document_types = ['postmortem', 'guide', 'troubleshoot', 'incident report', 'deployment note']
    for doc_type in document_types:
        if doc_type in question_lower:
            entities.append(Entity(
                entity_type=EntityType.DOCUMENT_TYPE,
                value=doc_type,
                confidence=0.75,
                context=doc_type
            ))
    
    # Remove duplicate entities
    seen_entities = set()
    unique_entities = []
    for entity in entities:
        entity_key = (entity.entity_type, entity.value.lower())
        if entity_key not in seen_entities:
            seen_entities.add(entity_key)
            unique_entities.append(entity)
    
    return unique_entities


def create_structured_investigation_plan(question: str, entities: List[Entity]) -> InvestigationPlan:
    """
    Create a structured investigation plan based on evidence-based reasoning.
    The Planner reasons about what evidence is needed rather than claiming facts.
    """
    plan = InvestigationPlan()
    
    # Determine the primary objective based on question analysis
    plan.objective = determine_objective(question, entities)
    
    # Add entities to the plan
    plan.entities = entities
    
    # Generate required evidence based on question type and entities
    plan.required_evidence = generate_required_evidence(question, entities)
    
    # Create investigation tasks based on what needs to be discovered
    plan.investigation_tasks = generate_investigation_tasks(question, entities, plan.required_evidence)
    
    # Identify unanswered questions that need to be resolved
    plan.unanswered_questions = generate_unanswered_questions(question, entities)
    
    # Add reasoning about the investigation approach
    plan.reasoning = generate_reasoning(question, entities, plan)
    
    return plan


def determine_objective(question: str, entities: List[Entity]) -> str:
    """
    Determine the primary objective of the investigation based on question analysis.
    """
    question_lower = question.lower()
    
    # Deployment-related questions
    if any(e.entity_type == EntityType.DEPLOYMENT for e in entities):
        if 'slow' in question_lower or 'latency' in question_lower:
            return "Investigate whether deployment caused performance degradation and identify causal relationship"
        elif 'down' in question_lower or 'outage' in question_lower:
            return "Investigate whether deployment caused service outage and determine root cause"
        else:
            return "Investigate relationship between deployment and reported issue"
    
    # Historical incident questions
    if 'seen this before' in question_lower or 'similar' in question_lower or 'historical' in question_lower:
        return "Identify and analyze historical incidents similar to the reported issue"
    
    # Contradiction/troubleshooting questions
    if 'contradiction' in question_lower or 'conflict' in question_lower or 'troubleshoot' in question_lower:
        return "Identify contradictions in documentation and determine correct guidance"
    
    # General incident investigation
    if any(e.entity_type == EntityType.INCIDENT_ID for e in entities):
        return "Investigate specific incident and gather comprehensive evidence"
    
    # Symptom-based investigation
    if any(e.entity_type == EntityType.SYMPTOM for e in entities):
        return "Investigate reported symptom and identify root cause"
    
    # Default objective
    return "Investigate reported issue and gather evidence to answer the question"


def generate_required_evidence(question: str, entities: List[Entity]) -> List[RequiredEvidence]:
    """
    Generate required evidence based on what needs to be discovered to answer the question.
    """
    required_evidence = []
    question_lower = question.lower()
    
    # Get service entity if present
    service_entity = next((e for e in entities if e.entity_type == EntityType.SERVICE), None)
    service_name = service_entity.value if service_entity else "the service"
    
    # Get date entity if present
    date_entity = next((e for e in entities if e.entity_type == EntityType.DATE), None)
    
    # Get deployment entity if present
    deployment_entity = next((e for e in entities if e.entity_type == EntityType.DEPLOYMENT), None)
    
    # Deployment-related evidence requirements
    if deployment_entity:
        required_evidence.append(RequiredEvidence(
            evidence_type="deployment_records",
            description=f"Deployment records for {service_name} around the incident timeframe",
            source_suggestions=["deployment notes", "release notes", "changelogs"],
            critical=True
        ))
        required_evidence.append(RequiredEvidence(
            evidence_type="deployment_incident_correlation",
            description="Evidence establishing temporal relationship between deployment and incident",
            source_suggestions=["incident reports", "monitoring data", "logs"],
            critical=True
        ))
        required_evidence.append(RequiredEvidence(
            evidence_type="causal_analysis",
            description="Evidence establishing whether deployment caused the incident or is merely correlated",
            source_suggestions=["postmortems", "root cause analysis", "technical analysis"],
            critical=True
        ))
    
    # Historical incident evidence requirements
    if 'seen this before' in question_lower or 'similar' in question_lower:
        required_evidence.append(RequiredEvidence(
            evidence_type="historical_incidents",
            description=f"Previous incidents involving {service_name} with similar symptoms",
            source_suggestions=["incident reports", "postmortems", "troubleshooting guides"],
            critical=True
        ))
        required_evidence.append(RequiredEvidence(
            evidence_type="root_cause_comparison",
            description="Comparison of root causes between current and historical incidents",
            source_suggestions=["postmortems", "technical documentation"],
            critical=True
        ))
    
    # General incident investigation evidence
    if any(e.entity_type == EntityType.INCIDENT_ID for e in entities):
        required_evidence.append(RequiredEvidence(
            evidence_type="incident_details",
            description="Comprehensive details about the specific incident",
            source_suggestions=["incident reports", "postmortems", "runbooks"],
            critical=True
        ))
        required_evidence.append(RequiredEvidence(
            evidence_type="timeline",
            description="Complete timeline of events during the incident",
            source_suggestions=["incident reports", "monitoring data", "logs"],
            critical=True
        ))
    
    # Symptom-based evidence requirements
    if any(e.entity_type == EntityType.SYMPTOM for e in entities):
        required_evidence.append(RequiredEvidence(
            evidence_type="symptom_analysis",
            description="Detailed analysis of the reported symptom and its manifestations",
            source_suggestions=["incident reports", "monitoring data", "user reports"],
            critical=True
        ))
        required_evidence.append(RequiredEvidence(
            evidence_type="root_cause",
            description="Root cause analysis explaining why the symptom occurred",
            source_suggestions=["postmortems", "technical analysis", "debugging reports"],
            critical=True
        ))
    
    # Date-specific evidence
    if date_entity:
        required_evidence.append(RequiredEvidence(
            evidence_type="timeframe_events",
            description=f"Events and changes around {date_entity.value}",
            source_suggestions=["deployment notes", "incident reports", "change logs"],
            critical=True
        ))
    
    # Default evidence requirements
    if not required_evidence:
        required_evidence.append(RequiredEvidence(
            evidence_type="incident_information",
            description="Basic information about the reported issue",
            source_suggestions=["incident reports", "documentation"],
            critical=True
        ))
    
    return required_evidence


def generate_investigation_tasks(question: str, entities: List[Entity], required_evidence: List[RequiredEvidence]) -> List[InvestigationTask]:
    """
    Generate specific investigation tasks based on required evidence.
    """
    tasks = []
    task_counter = 1
    
    # Get service entity if present
    service_entity = next((e for e in entities if e.entity_type == EntityType.SERVICE), None)
    service_name = service_entity.value if service_entity else "service"
    
    # Get incident ID if present
    incident_entity = next((e for e in entities if e.entity_type == EntityType.INCIDENT_ID), None)
    
    # Get deployment entity if present
    deployment_entity = next((e for e in entities if e.entity_type == EntityType.DEPLOYMENT), None)
    
    # Task 1: Initial information gathering
    if incident_entity:
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description=f"Search for incident {incident_entity.value} to gather basic information",
            task_type="search",
            priority="high",
            dependencies=[],
            expected_outcome="Incident report and basic details"
        ))
        task_counter += 1
    elif service_entity:
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description=f"Search for incidents involving {service_name}",
            task_type="search",
            priority="high",
            dependencies=[],
            expected_outcome="List of relevant incidents"
        ))
        task_counter += 1
    
    # Task 2: Deployment-specific investigation
    if deployment_entity:
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description=f"Identify deployments for {service_name} around the incident timeframe",
            task_type="search",
            priority="high",
            dependencies=[],
            expected_outcome="Deployment records and timestamps"
        ))
        task_counter += 1
        
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description="Analyze temporal relationship between deployment and incident onset",
            task_type="analyze",
            priority="high",
            dependencies=[f"task_{task_counter-1}"],
            expected_outcome="Timeline correlation analysis"
        ))
        task_counter += 1
        
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description="Investigate causal links between deployment changes and incident symptoms",
            task_type="analyze",
            priority="high",
            dependencies=[f"task_{task_counter-1}"],
            expected_outcome="Causal relationship assessment"
        ))
        task_counter += 1
    
    # Task 3: Historical comparison
    question_lower = question.lower()
    if 'seen this before' in question_lower or 'similar' in question_lower:
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description=f"Search for historical incidents with similar symptoms in {service_name}",
            task_type="search",
            priority="medium",
            dependencies=[],
            expected_outcome="List of similar historical incidents"
        ))
        task_counter += 1
        
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description="Compare root causes and resolutions between current and historical incidents",
            task_type="compare",
            priority="medium",
            dependencies=[f"task_{task_counter-1}"],
            expected_outcome="Comparison analysis and pattern identification"
        ))
        task_counter += 1
    
    # Task 4: Contradiction detection
    if 'contradiction' in question_lower or 'conflict' in question_lower:
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description="Search for documentation related to the issue to identify conflicting information",
            task_type="search",
            priority="high",
            dependencies=[],
            expected_outcome="Relevant documentation with potential conflicts"
        ))
        task_counter += 1
        
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description="Analyze documentation for contradictions and outdated guidance",
            task_type="analyze",
            priority="high",
            dependencies=[f"task_{task_counter-1}"],
            expected_outcome="List of contradictions and recommended guidance"
        ))
        task_counter += 1
    
    # Task 5: Root cause investigation
    if any(e.entity_type == EntityType.SYMPTOM for e in entities):
        tasks.append(InvestigationTask(
            task_id=f"task_{task_counter}",
            description="Investigate root cause of reported symptom",
            task_type="search",
            priority="high",
            dependencies=[],
            expected_outcome="Root cause analysis and contributing factors"
        ))
        task_counter += 1
    
    # Task 6: Evidence sufficiency assessment
    tasks.append(InvestigationTask(
        task_id=f"task_{task_counter}",
        description="Assess whether gathered evidence is sufficient to answer the investigation question",
        task_type="analyze",
        priority="medium",
        dependencies=[f"task_{i}" for i in range(1, task_counter)],
        expected_outcome="Evidence sufficiency determination and gaps identification"
    ))
    
    return tasks


def generate_unanswered_questions(question: str, entities: List[Entity]) -> List[str]:
    """
    Generate specific questions that need to be answered during the investigation.
    """
    unanswered = []
    question_lower = question.lower()
    
    # Get service entity if present
    service_entity = next((e for e in entities if e.entity_type == EntityType.SERVICE), None)
    service_name = service_entity.value if service_entity else "the service"
    
    # Get deployment entity if present
    deployment_entity = next((e for e in entities if e.entity_type == EntityType.DEPLOYMENT), None)
    
    # Deployment-related questions
    if deployment_entity:
        unanswered.append(f"What deployment occurred for {service_name} around the incident timeframe?")
        unanswered.append("What changes were included in the deployment?")
        unanswered.append("Did the deployment occur before, during, or after the incident started?")
        unanswered.append("Is there evidence that the deployment caused the incident, or is it merely temporal correlation?")
        unanswered.append("What testing was performed before the deployment?")
    
    # Historical comparison questions
    if 'seen this before' in question_lower or 'similar' in question_lower:
        unanswered.append(f"Have similar incidents occurred with {service_name} in the past?")
        unanswered.append("What were the root causes of similar historical incidents?")
        unanswered.append("How were similar incidents resolved in the past?")
        unanswered.append("Are there patterns in the timing or circumstances of similar incidents?")
    
    # General incident questions
    unanswered.append("What exactly happened during the incident?")
    unanswered.append("When did the incident start and end?")
    unanswered.append("What services or components were affected?")
    unanswered.append("What was the root cause of the incident?")
    unanswered.append("How was the incident resolved?")
    unanswered.append("What preventive measures have been implemented?")
    
    # Symptom-specific questions
    if any(e.entity_type == EntityType.SYMPTOM for e in entities):
        symptom_entity = next(e for e in entities if e.entity_type == EntityType.SYMPTOM)
        unanswered.append(f"What caused the {symptom_entity.value} symptom?")
        unanswered.append("Were there any precursor warnings or indicators?")
        unanswered.append("What monitoring or logging captured the symptom?")
    
    return unanswered


def generate_reasoning(question: str, entities: List[Entity], plan: InvestigationPlan) -> str:
    """
    Generate reasoning about the investigation approach.
    """
    reasoning_parts = []
    
    reasoning_parts.append("The investigation will proceed by first gathering foundational information about the reported issue.")
    
    # Add entity-based reasoning
    if entities:
        entity_types = [e.entity_type.value for e in entities]
        reasoning_parts.append(f"Identified entities include: {', '.join(entity_types)}. These will guide the search strategy.")
    
    # Add evidence-based reasoning
    if plan.required_evidence:
        critical_evidence = [e for e in plan.required_evidence if e.critical]
        if critical_evidence:
            reasoning_parts.append(f"Critical evidence required: {', '.join([e.evidence_type for e in critical_evidence])}.")
    
    # Add task-based reasoning
    if plan.investigation_tasks:
        high_priority_tasks = [t for t in plan.investigation_tasks if t.priority == "high"]
        if high_priority_tasks:
            reasoning_parts.append(f"High-priority tasks focus on: {', '.join([t.description[:50] + '...' for t in high_priority_tasks])}.")
    
    # Add approach reasoning
    question_lower = question.lower()
    if 'deployment' in question_lower:
        reasoning_parts.append("The investigation will specifically examine the temporal and causal relationship between deployment activities and the incident, avoiding assumptions of causation without evidence.")
    elif 'seen this before' in question_lower or 'similar' in question_lower:
        reasoning_parts.append("The investigation will compare the current incident with historical patterns to identify similarities and differences in root causes and resolutions.")
    elif 'contradiction' in question_lower:
        reasoning_parts.append("The investigation will systematically examine documentation for conflicting information and provide evidence-based recommendations.")
    
    reasoning_parts.append("The investigation will iterate until sufficient evidence is gathered or the maximum iteration limit is reached.")
    
    return " ".join(reasoning_parts)