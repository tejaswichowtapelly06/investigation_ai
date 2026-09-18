import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.graph.state import InvestigationState, InvestigationPlan, Entity, EntityType
from app.tools.interfaces import SearchTool, SearchFilters, DocumentResult
from app.tools.tool_registry import get_tool_registry

logger = logging.getLogger(__name__)


def get_timestamp() -> str:
    """Get current timestamp for logging."""
    return datetime.now().isoformat()


def researcher_agent(state: InvestigationState) -> InvestigationState:
    """
    Researcher Agent: Performs searches based on investigation plan and discovered evidence.
    Implements multi-hop investigation using tool interfaces with dependency injection.
    """
    logger.info("=" * 60)
    logger.info("RESEARCHER AGENT - Starting investigation")
    logger.info("=" * 60)
    logger.info(f"Iteration: {state['iteration_count']}")
    
    # Get search tool from registry (dependency injection)
    try:
        search_tool = get_tool_registry().get_search_tool()
        logger.info("RESEARCHER - Using injected search tool")
    except ValueError as e:
        logger.error(f"RESEARCHER - No search tool registered: {e}")
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        return state
    
    # Get investigation plan
    investigation_plan = state.get("investigation_plan")
    if isinstance(investigation_plan, InvestigationPlan):
        plan_tasks = investigation_plan.investigation_tasks
        plan_entities = investigation_plan.entities
    else:
        plan_tasks = []
        plan_entities = []
    
    # Get current state
    discovered_entities = state.get("discovered_entities", [])
    searches_performed = state.get("searches_performed", [])
    retrieved_documents = state.get("retrieved_documents", [])
    iteration_count = state.get("iteration_count", 0)
    
    # Get evidence gaps from previous iteration (if any)
    evidence_gaps = state.get("evidence_gaps", [])
    
    # Determine next investigation task
    next_task = determine_next_task(plan_tasks, searches_performed, discovered_entities, iteration_count, evidence_gaps)
    
    if not next_task:
        logger.info("RESEARCHER - No more tasks to perform in this iteration")
        state["iteration_count"] = iteration_count + 1
        return state
    
    # Handle both InvestigationTask objects and dict tasks
    task_id = next_task.task_id if hasattr(next_task, 'task_id') else next_task.get("task_id", "unknown")
    task_description = next_task.description if hasattr(next_task, 'description') else next_task.get("description", "unknown")
    
    logger.info(f"RESEARCHER - Selected task: {task_description}")
    if evidence_gaps:
        logger.info(f"RESEARCHER - Evidence gaps from previous iteration: {evidence_gaps}")
    
    # Execute the task using injected tool
    try:
        search_result = execute_task(next_task, discovered_entities, search_tool, evidence_gaps)
        
        # Log search results
        logger.info(f"RESEARCHER - Tool: {search_result.get('tool_used', 'unknown')}")
        logger.info(f"RESEARCHER - Query/Filters: {search_result.get('query_filters', 'unknown')}")
        logger.info(f"RESEARCHER - Documents found: {len(search_result.get('documents', []))}")
        
        # Extract newly discovered entities
        new_entities = extract_entities_from_results(search_result.get("documents", []))
        logger.info(f"RESEARCHER - Newly discovered entities: {len(new_entities)}")
        for entity in new_entities:
            logger.info(f"  - {entity.entity_type.value}: {entity.value}")
        
        # Update discovered entities
        updated_entities = merge_entities(discovered_entities, new_entities)
        state["discovered_entities"] = updated_entities
        
        # Convert DocumentResult to dict for compatibility
        new_documents_dict = [doc.model_dump() for doc in search_result.get("documents", [])]
        
        # Filter out duplicate documents
        new_documents_dict = filter_duplicate_documents(new_documents_dict, retrieved_documents)
        
        # Add new documents to state
        retrieved_documents.extend(new_documents_dict)
        
        # Record search in searches_performed
        searches_performed.append({
            "task_id": task_id,
            "tool_used": search_result.get("tool_used"),
            "query_filters": search_result.get("query_filters"),
            "results_count": len(new_documents_dict),
            "new_entities": [e.model_dump() for e in new_entities],
            "addressed_gaps": evidence_gaps,
            "timestamp": get_timestamp()
        })
        
        # Update state
        state["searches_performed"] = searches_performed
        state["retrieved_documents"] = retrieved_documents
        state["iteration_count"] = iteration_count + 1
        
        # Add investigation trace entry
        try:
            trace_entry = {
                "iteration": iteration_count,
                "agent": "researcher",
                "action": "document_retrieval",
                "task_id": task_id,
                "task_description": task_description,
                "tool_used": search_result.get("tool_used"),
                "query_filters": search_result.get("query_filters"),
                "documents_found": len(new_documents_dict),
                "new_entities_count": len(new_entities),
                "total_documents": len(retrieved_documents),
                "total_entities": len(updated_entities),
                "addressed_gaps": evidence_gaps,
                "timestamp": get_timestamp()
            }
            investigation_trace = state.get("investigation_trace", [])
            investigation_trace.append(trace_entry)
            state["investigation_trace"] = investigation_trace
            logger.info(f"RESEARCHER - Added trace entry for iteration {iteration_count}")
        except Exception as e:
            logger.error(f"RESEARCHER - Error adding trace entry: {e}")
        
        logger.info(f"RESEARCHER - Total documents retrieved: {len(retrieved_documents)}")
        logger.info(f"RESEARCHER - Total discovered entities: {len(updated_entities)}")
        
    except Exception as e:
        logger.error(f"RESEARCHER - Error executing task '{task_description}': {e}")
        # Continue with next iteration even if one task fails
        state["iteration_count"] = iteration_count + 1
    
    logger.info("RESEARCHER AGENT - Completed")
    logger.info("=" * 60)
    
    return state


def determine_next_task(
    plan_tasks: List,
    searches_performed: List[Dict[str, Any]],
    discovered_entities: List[Entity],
    iteration_count: int,
    evidence_gaps: List[str] = []
) -> Optional[Any]:
    """
    Determine which investigation task should be performed next.
    Implements multi-hop investigation logic and uses evidence gaps.
    """
    # Get already performed task IDs
    performed_task_ids = {search.get("task_id") for search in searches_performed}
    
    # Helper function to extract task properties
    def get_task_props(task):
        if hasattr(task, 'task_id'):
            return task.task_id, task.priority, task.dependencies
        else:
            return task.get("task_id"), task.get("priority", "medium"), task.get("dependencies", [])
    
    # First priority: Address evidence gaps from previous iteration
    if evidence_gaps and iteration_count > 0:
        logger.info(f"RESEARCHER - Addressing evidence gaps: {evidence_gaps}")
        return generate_gap_addressing_task(evidence_gaps, discovered_entities, iteration_count)
    
    # Second: Try to find high-priority tasks that haven't been performed
    for task in plan_tasks:
        task_id, priority, dependencies = get_task_props(task)
        if task_id not in performed_task_ids and priority == "high":
            # Check if dependencies are satisfied
            if all(dep in performed_task_ids for dep in dependencies):
                return task
    
    # Third: If no high-priority tasks, try medium-priority tasks
    for task in plan_tasks:
        task_id, priority, dependencies = get_task_props(task)
        if task_id not in performed_task_ids and priority == "medium":
            if all(dep in performed_task_ids for dep in dependencies):
                return task
    
    # Fourth: Multi-hop - Generate follow-up tasks based on discovered entities
    if discovered_entities and iteration_count > 0:
        return generate_follow_up_task(discovered_entities, searches_performed)
    
    # Default: return first unperformed task
    for task in plan_tasks:
        task_id, _, _ = get_task_props(task)
        if task_id not in performed_task_ids:
            return task
    
    return None


def generate_gap_addressing_task(evidence_gaps: List[str], discovered_entities: List[Entity], iteration_count: int) -> Dict:
    """
    Generate a task to address specific evidence gaps.
    """
    entity_dict = {e.entity_type: e.value for e in discovered_entities}
    
    # Determine search strategy based on evidence gaps
    if any("root_cause" in gap.lower() for gap in evidence_gaps):
        return {
            "task_id": f"gap_root_cause_{iteration_count}",
            "description": "Search for root cause information",
            "task_type": "search",
            "priority": "high",
            "dependencies": [],
            "expected_outcome": "Root cause documentation"
        }
    
    if any("deployment" in gap.lower() for gap in evidence_gaps):
        if EntityType.VERSION in entity_dict:
            return {
                "task_id": f"gap_deployment_{entity_dict[EntityType.VERSION]}",
                "description": f"Search for deployment information for version {entity_dict[EntityType.VERSION]}",
                "task_type": "search",
                "priority": "high",
                "dependencies": [],
                "expected_outcome": "Deployment records"
            }
    
    if any("timeline" in gap.lower() or "timeframe" in gap.lower() for gap in evidence_gaps):
        return {
            "task_id": f"gap_timeline_{iteration_count}",
            "description": "Search for timeline and timeframe information",
            "task_type": "search",
            "priority": "medium",
            "dependencies": [],
            "expected_outcome": "Timeline documentation"
        }
    
    # Default gap addressing
    return {
        "task_id": f"gap_general_{iteration_count}",
        "description": f"Search to address evidence gaps: {', '.join(evidence_gaps[:2])}",
        "task_type": "search",
        "priority": "high",
        "dependencies": [],
        "expected_outcome": "Evidence to fill gaps"
    }


def generate_follow_up_task(
    discovered_entities: List[Entity],
    searches_performed: List[Dict[str, Any]]
) -> Optional[Dict]:
    """
    Generate a follow-up task based on newly discovered entities.
    This enables multi-hop investigation.
    """
    # Get entity types and values
    entity_dict = {e.entity_type: e.value for e in discovered_entities}
    
    # Get already performed searches
    performed_searches = {search.get("query_filters", "") for search in searches_performed}
    
    # Priority 1: If we discovered a version, search for deployment
    if EntityType.VERSION in entity_dict:
        version = entity_dict[EntityType.VERSION]
        version_search = f"version:{version}"
        if version_search not in performed_searches:
            return {
                "task_id": f"followup_version_{version}",
                "description": f"Search for deployment and documents related to version {version}",
                "task_type": "search",
                "priority": "high",
                "dependencies": [],
                "expected_outcome": "Deployment records and version-specific documentation"
            }
    
    # Priority 2: If we discovered a service, search for historical incidents
    if EntityType.SERVICE in entity_dict:
        service = entity_dict[EntityType.SERVICE]
        service_search = f"service:{service}"
        if service_search not in performed_searches:
            return {
                "task_id": f"followup_service_{service}",
                "description": f"Search for historical incidents involving {service}",
                "task_type": "search",
                "priority": "medium",
                "dependencies": [],
                "expected_outcome": "Historical incident patterns"
            }
    
    # Priority 3: If we discovered an incident ID, search for related documents
    if EntityType.INCIDENT_ID in entity_dict:
        incident_id = entity_dict[EntityType.INCIDENT_ID]
        incident_search = f"incident:{incident_id}"
        if incident_search not in performed_searches:
            return {
                "task_id": f"followup_incident_{incident_id}",
                "description": f"Search for documents related to incident {incident_id}",
                "task_type": "search",
                "priority": "high",
                "dependencies": [],
                "expected_outcome": "Related incident documentation"
            }
    
    # Priority 4: If we discovered a deployment, search for service documents
    if EntityType.DEPLOYMENT in entity_dict:
        deployment = entity_dict[EntityType.DEPLOYMENT]
        deployment_search = f"deployment:{deployment}"
        if deployment_search not in performed_searches:
            return {
                "task_id": f"followup_deployment_{deployment}",
                "description": f"Search for documents related to deployment {deployment}",
                "task_type": "search",
                "priority": "medium",
                "dependencies": [],
                "expected_outcome": "Deployment-related documentation"
            }
    
    return None


def execute_task(task: Any, discovered_entities: List[Entity], database: SearchTool, evidence_gaps: List[str] = []) -> Dict[str, Any]:
    """
    Execute a investigation task using the appropriate tool.
    """
    entity_dict = {e.entity_type: e.value for e in discovered_entities}
    
    # Handle both InvestigationTask objects and dict tasks
    if hasattr(task, 'description'):
        task_description = task.description.lower()
    else:
        task_description = task.get("description", "").lower()
    
    # Determine which tool to use based on task description
    if "deployment" in task_description and "version" in task_description:
        # Search by version for deployment investigation
        if EntityType.VERSION in entity_dict:
            version = entity_dict[EntityType.VERSION]
            result = database.search_by_version(version)
            return {
                "tool_used": "search_by_version",
                "query_filters": f"version: {version}",
                "documents": result.documents
            }
    
    elif "historical" in task_description or "similar" in task_description:
        # Search for historical incidents
        service = entity_dict.get(EntityType.SERVICE, "")
        symptom = entity_dict.get(EntityType.SYMPTOM, "")
        result = database.search_historical_incidents(service, symptom)
        return {
            "tool_used": "search_historical_incidents",
            "query_filters": f"service: {service}, symptom: {symptom}",
            "documents": result.documents
        }
    
    elif "service" in task_description and EntityType.SERVICE in entity_dict:
        # Search by service
        service = entity_dict[EntityType.SERVICE]
        result = database.search_by_service(service)
        return {
            "tool_used": "search_by_service",
            "query_filters": f"service: {service}",
            "documents": result.documents
        }
    
    elif "incident" in task_description and EntityType.INCIDENT_ID in entity_dict:
        # Get specific incident document
        incident_id = entity_dict[EntityType.INCIDENT_ID]
        doc = database.get_document(incident_id)
        if doc:
            return {
                "tool_used": "get_document",
                "query_filters": f"document_id: {incident_id}",
                "documents": [doc]
            }
        else:
            # Fallback to search by incident_id in content
            filters = SearchFilters(incident_id=incident_id)
            result = database.metadata_search(filters)
            return {
                "tool_used": "metadata_search",
                "query_filters": f"incident_id: {incident_id}",
                "documents": result.documents
            }
    
    elif "related" in task_description and len(discovered_entities) > 0:
        # Search for related documents using the most recent document
        if has_document_entities(discovered_entities):
            # Use semantic search with discovered entities
            query = " ".join([e.value for e in discovered_entities[:3]])
            result = database.semantic_search(query)
            return {
                "tool_used": "semantic_search",
                "query_filters": f"query: {query}",
                "documents": result.documents
            }
    
    elif "root cause" in task_description:
        # Search for root cause information
        if EntityType.SERVICE in entity_dict:
            query = f"{entity_dict[EntityType.SERVICE]} root cause"
        else:
            query = "root cause"
        result = database.semantic_search(query)
        return {
            "tool_used": "semantic_search",
            "query_filters": f"query: {query}",
            "documents": result.documents
        }
    
    # Default: semantic search based on task description
    query = " ".join([word for word in task_description.split() if len(word) > 3])
    result = database.semantic_search(query)
    return {
        "tool_used": "semantic_search",
        "query_filters": f"query: {query}",
        "documents": result.documents
    }


def has_document_entities(discovered_entities: List[Entity]) -> bool:
    """Check if the state has document-related entities."""
    return any(e.entity_type in [EntityType.INCIDENT_ID, EntityType.DOCUMENT_TYPE] for e in discovered_entities)


def extract_entities_from_results(documents: List[DocumentResult]) -> List[Entity]:
    """
    Extract newly discovered entities from search results.
    """
    new_entities = []
    
    for doc in documents:
        # Extract service
        if doc.service:
            new_entities.append(Entity(
                entity_type=EntityType.SERVICE,
                value=doc.service,
                confidence=0.9,
                context=f"From document {doc.document_id}"
            ))
        
        # Extract version
        if doc.version:
            new_entities.append(Entity(
                entity_type=EntityType.VERSION,
                value=doc.version,
                confidence=0.85,
                context=f"From document {doc.document_id}"
            ))
        
        # Extract incident ID
        if doc.incident_id:
            new_entities.append(Entity(
                entity_type=EntityType.INCIDENT_ID,
                value=doc.incident_id,
                confidence=0.95,
                context=f"From document {doc.document_id}"
            ))
        
        # Extract document type
        if doc.document_type:
            new_entities.append(Entity(
                entity_type=EntityType.DOCUMENT_TYPE,
                value=doc.document_type,
                confidence=0.8,
                context=f"From document {doc.document_id}"
            ))
        
        # Extract deployment-related information
        if "deployment" in doc.content.lower() or doc.document_type == "deployment_note":
            new_entities.append(Entity(
                entity_type=EntityType.DEPLOYMENT,
                value=doc.document_id if doc.document_type == "deployment_note" else "deployment",
                confidence=0.75,
                context=f"From document {doc.document_id}"
            ))
    
    return new_entities


def merge_entities(existing_entities: List[Entity], new_entities: List[Entity]) -> List[Entity]:
    """
    Merge new entities with existing ones, avoiding duplicates.
    """
    entity_map = {(e.entity_type, e.value.lower()): e for e in existing_entities}
    
    for entity in new_entities:
        key = (entity.entity_type, entity.value.lower())
        if key not in entity_map:
            entity_map[key] = entity
    
    return list(entity_map.values())


def filter_duplicate_documents(new_documents: List[Dict[str, Any]], existing_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out documents that are already in the existing documents list.
    """
    existing_ids = {doc.get("document_id") for doc in existing_documents}
    
    filtered = []
    for doc in new_documents:
        if doc.get("document_id") not in existing_ids:
            filtered.append(doc)
    
    return filtered