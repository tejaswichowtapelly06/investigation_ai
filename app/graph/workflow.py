import logging
from typing import Literal
from datetime import datetime
from langgraph.graph import StateGraph, END
from app.graph.state import InvestigationState, InvestigationPlan
from app.agents.planner import planner_agent
from app.agents.researcher import researcher_agent
from app.agents.analyst import analyst_agent
from app.tools.analysis_models import Classification
from app.config.settings import settings
from app.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def create_investigation_graph(tool_registry: ToolRegistry = None):
    """
    Create the LangGraph investigation workflow.
    
    Args:
        tool_registry: ToolRegistry instance for dependency injection.
                      If None, agents will use global registry (deprecated).
    """
    logger.info("Creating investigation graph")
    
    # Create the graph
    workflow = StateGraph(InvestigationState)
    
    # Add nodes with tool_registry parameter
    workflow.add_node("planner", planner_agent)
    workflow.add_node("researcher", lambda state: researcher_agent(state, tool_registry))
    workflow.add_node("analyst", lambda state: analyst_agent(state, tool_registry))
    workflow.add_node("report", report_generator)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Add edges
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "analyst")
    
    # Add conditional edge from analyst
    workflow.add_conditional_edges(
        "analyst",
        should_continue_research,
        {
            "researcher": "researcher",
            "report": "report"
        }
    )
    
    # Add edge to END
    workflow.add_edge("report", END)
    
    # Compile the graph
    app = workflow.compile()
    
    logger.info("Investigation graph created successfully")
    
    return app


def should_continue_research(state: InvestigationState) -> Literal["researcher", "report"]:
    """
    Conditional routing function: determines whether to continue research or generate report.
    """
    logger.info("=" * 60)
    logger.info("ROUTING DECISION")
    logger.info("=" * 60)
    
    evidence_sufficient = state.get("evidence_sufficient", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", settings.MAX_ITERATIONS)
    
    logger.info(f"Evidence sufficient: {evidence_sufficient}")
    logger.info(f"Iteration count: {iteration_count}/{max_iterations}")
    
    # Check if we've reached max iterations
    if iteration_count >= max_iterations:
        logger.info("ROUTING - Max iterations reached, proceeding to report")
        logger.info("=" * 60)
        return "report"
    
    # Check if evidence is sufficient
    if evidence_sufficient:
        logger.info("ROUTING - Evidence sufficient, proceeding to report")
        logger.info("=" * 60)
        return "report"
    else:
        logger.info("ROUTING - Evidence insufficient, continuing research")
        logger.info("=" * 60)
        return "researcher"


def report_generator(state: InvestigationState) -> InvestigationState:
    """
    Report Generator node: Synthesizes final investigation report.
    """
    logger.info("=" * 60)
    logger.info("REPORT GENERATOR - Creating final report")
    logger.info("=" * 60)
    
    question = state["question"]
    investigation_plan = state.get("investigation_plan", {})
    evidence = state.get("evidence", [])
    contradictions = state.get("contradictions", [])
    related_incidents = state.get("related_incidents", [])
    findings = state.get("findings", [])
    evidence_sufficient = state.get("evidence_sufficient", False)
    iteration_count = state.get("iteration_count", 0)
    
    # Extract entities from investigation plan if it's a structured plan
    if isinstance(investigation_plan, InvestigationPlan):
        entities_dict = {e.entity_type.value: e.value for e in investigation_plan.entities}
        plan_objective = investigation_plan.objective
        plan_reasoning = investigation_plan.reasoning
    else:
        entities_dict = investigation_plan.get("entities", {})
        plan_objective = investigation_plan.get("objective", "Investigate reported issue")
        plan_reasoning = ""
    
    # Generate final answer
    if evidence_sufficient:
        final_answer = generate_sufficient_report(
            question, entities_dict, evidence, contradictions, related_incidents, findings,
            plan_objective, plan_reasoning
        )
        state["status"] = "completed"
    else:
        final_answer = generate_insufficient_report(
            question, entities_dict, evidence, contradictions, related_incidents, findings, iteration_count,
            plan_objective, plan_reasoning
        )
        state["status"] = "insufficient_evidence"
    
    state["final_answer"] = final_answer
    state["completed_at"] = datetime.now().isoformat()
    
    logger.info("REPORT GENERATOR - Completed")
    logger.info("=" * 60)
    
    return state


def generate_sufficient_report(
    question: str,
    entities: dict,
    evidence: list,
    contradictions: list,
    related_incidents: list,
    findings: list,
    plan_objective: str = "",
    plan_reasoning: str = ""
) -> str:
    """
    Generate report when evidence is sufficient.
    """
    report_lines = [
        "=" * 60,
        "INVESTIGATION REPORT",
        "=" * 60,
        f"Question: {question}",
        f"Status: COMPLETE - Sufficient evidence gathered",
        "",
        "--- INVESTIGATION OBJECTIVE ---",
        plan_objective if plan_objective else "Investigate reported issue",
    ]
    
    if plan_reasoning:
        report_lines.extend([
            "",
            "--- INVESTIGATION REASONING ---",
            plan_reasoning
        ])
    
    report_lines.extend([
        "",
        "--- SUMMARY ---",
    ])
    
    # Add findings
    for finding in findings:
        report_lines.append(f"• {finding}")
    
    # Add entities
    if entities:
        report_lines.append("")
        report_lines.append("--- IDENTIFIED ENTITIES ---")
        for key, value in entities.items():
            if value:
                report_lines.append(f"• {key}: {value}")
    
    # Add evidence summary
    if evidence:
        report_lines.append("")
        report_lines.append(f"--- EVIDENCE ({len(evidence)} items) ---")
        for i, ev in enumerate(evidence[:5], 1):  # Limit to first 5
            report_lines.append(f"{i}. {ev.get('source_type', 'unknown')} - {ev.get('service', 'unknown service')}")
            if ev.get('incident_id'):
                report_lines.append(f"   Incident ID: {ev['incident_id']}")
            if ev.get('date'):
                report_lines.append(f"   Date: {ev['date']}")
            if ev.get('severity'):
                report_lines.append(f"   Severity: {ev['severity']}")
    
    # Add contradictions
    if contradictions:
        report_lines.append("")
        report_lines.append(f"--- CONTRADICTIONS ({len(contradictions)}) ---")
        for contradiction in contradictions[:3]:  # Limit to first 3
            # Handle both dict and structured contradiction objects
            if isinstance(contradiction, dict):
                contr_type = contradiction.get("contradiction_type", "unknown")
                contr_desc = contradiction.get("description", "unknown")
                resolution = contradiction.get("resolution", "")
            else:
                contr_type = contradiction.contradiction_type
                contr_desc = contradiction.description
                resolution = contradiction.resolution
            
            report_lines.append(f"[WARNING] {contr_type}: {contr_desc}")
            if resolution:
                report_lines.append(f"    Resolution: {resolution}")
    
    # Add related incidents
    if related_incidents:
        report_lines.append("")
        report_lines.append(f"--- RELATED INCIDENTS ({len(related_incidents)} relationships) ---")
        for rel in related_incidents[:5]:  # Limit to first 5
            # Handle both dict and structured comparison objects
            if isinstance(rel, dict):
                # Legacy format
                incident_1 = rel.get("incident_1", {})
                incident_2 = rel.get("incident_2", {})
                result = rel.get("comparison_result", "unknown")
                incident_1_id = incident_1.get("id", "unknown")
                incident_2_id = incident_2.get("id", "unknown")
            else:
                # New structured format
                incident_1_id = rel.current_incident_id
                incident_2_id = rel.candidate_incident_id
                result = rel.classification.value
            
            report_lines.append(f"• {incident_1_id} ↔ {incident_2_id}: {result}")
    
    report_lines.append("")
    report_lines.append("--- CONCLUSION ---")
    report_lines.append("The investigation has gathered sufficient evidence to answer the question.")
    report_lines.append("All key findings have been documented above.")
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)


def generate_insufficient_report(
    question: str,
    entities: dict,
    evidence: list,
    contradictions: list,
    related_incidents: list,
    findings: list,
    iteration_count: int,
    plan_objective: str = "",
    plan_reasoning: str = ""
) -> str:
    """
    Generate report when evidence is insufficient.
    """
    report_lines = [
        "=" * 60,
        "INVESTIGATION REPORT",
        "=" * 60,
        f"Question: {question}",
        f"Status: INCOMPLETE - Insufficient evidence",
        f"Iterations completed: {iteration_count}",
        "",
        "--- INVESTIGATION OBJECTIVE ---",
        plan_objective if plan_objective else "Investigate reported issue",
    ]
    
    if plan_reasoning:
        report_lines.extend([
            "",
            "--- INVESTIGATION REASONING ---",
            plan_reasoning
        ])
    
    report_lines.extend([
        "",
        "--- SUMMARY ---",
    ])
    
    # Add findings
    for finding in findings:
        report_lines.append(f"• {finding}")
    
    # Add entities
    if entities:
        report_lines.append("")
        report_lines.append("--- IDENTIFIED ENTITIES ---")
        for key, value in entities.items():
            if value:
                report_lines.append(f"• {key}: {value}")
    
    # Add evidence summary
    if evidence:
        report_lines.append("")
        report_lines.append(f"--- EVIDENCE ({len(evidence)} items) ---")
        for i, ev in enumerate(evidence[:3], 1):  # Limit to first 3
            report_lines.append(f"{i}. {ev.get('source_type', 'unknown')} - {ev.get('service', 'unknown service')}")
    
    # Add contradictions
    if contradictions:
        report_lines.append("")
        report_lines.append(f"--- CONTRADICTIONS ({len(contradictions)}) ---")
        for contradiction in contradictions[:2]:  # Limit to first 2
            # Handle both dict and structured contradiction objects
            if isinstance(contradiction, dict):
                contr_type = contradiction.get("contradiction_type", "unknown")
                contr_desc = contradiction.get("description", "unknown")
            else:
                contr_type = contradiction.contradiction_type
                contr_desc = contradiction.description
            
            report_lines.append(f"[WARNING] {contr_type}: {contr_desc}")
    
    report_lines.append("")
    report_lines.append("--- EVIDENCE GAPS ---")
    report_lines.append("• Insufficient evidence to fully answer the investigation question")
    report_lines.append("• Additional searches may be required")
    report_lines.append("• Consider refining the search terms or expanding the scope")
    
    report_lines.append("")
    report_lines.append("--- CONCLUSION ---")
    report_lines.append("The investigation could not gather sufficient evidence within the iteration limit.")
    report_lines.append("Please review the findings above and consider adjusting the investigation parameters.")
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)


