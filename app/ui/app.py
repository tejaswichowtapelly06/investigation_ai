"""
Streamlit UI for investigation system.
Shows the investigation process: Planner → Researcher → Analyst → Report
"""
import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, List

# Page config
st.set_page_config(
    page_title="Investigation AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration
API_URL = "http://localhost:8000"

# Custom functions
def call_api(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Call the FastAPI backend."""
    try:
        url = f"{API_URL}{endpoint}"
        if method == "POST":
            response = requests.post(url, json=data, timeout=300)
        else:
            response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def display_trace_entry(entry: Dict[str, Any]):
    """Display a single investigation trace entry."""
    agent = entry.get("agent", "unknown")
    action = entry.get("action", "unknown")
    timestamp = entry.get("timestamp", "")
    
    with st.expander(f"📍 {agent.upper()}: {action} - {timestamp}", expanded=False):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write(f"**Agent:** {agent}")
            st.write(f"**Action:** {action}")
            st.write(f"**Iteration:** {entry.get('iteration', 0)}")
        
        with col2:
            # Display agent-specific information
            if agent == "planner":
                st.write(f"**Objective:** {entry.get('objective', '')}")
                st.write(f"**Entities:** {entry.get('entities', [])}")
                st.write(f"**Tasks:** {entry.get('task_count', 0)}")
            elif agent == "researcher":
                st.write(f"**Tool:** {entry.get('tool_used', '')}")
                st.write(f"**Documents Found:** {entry.get('documents_found', 0)}")
                st.write(f"**New Entities:** {entry.get('new_entities', [])}")
                st.write(f"**Document IDs:** {entry.get('document_ids', [])}")
            elif agent == "analyst":
                st.write(f"**Evidence Count:** {entry.get('evidence_count', 0)}")
                st.write(f"**Contradictions:** {entry.get('contradiction_count', 0)}")
                st.write(f"**Evidence Sufficient:** {entry.get('evidence_sufficient', False)}")
                st.write(f"**Gaps:** {entry.get('evidence_gaps', [])}")
            elif agent == "report":
                st.write(f"**Report Generated:** Yes")


def display_evidence(evidence_list: List[Dict]):
    """Display evidence items with clickable document IDs."""
    if not evidence_list:
        st.info("No evidence found")
        return
    
    for i, evidence in enumerate(evidence_list):
        with st.expander(f"📄 Evidence {i+1}: {evidence.get('claim', 'No claim')[:80]}...", expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write(f"**Document ID:** `{evidence.get('document_id', 'N/A')}`")
                st.write(f"**Type:** {evidence.get('evidence_type', 'unknown')}")
                st.write(f"**Confidence:** {evidence.get('confidence', 0):.2f}")
            
            with col2:
                st.write(f"**Claim:** {evidence.get('claim', 'No claim')}")
                if evidence.get('metadata'):
                    with st.expander("Metadata"):
                        st.json(evidence['metadata'])


def display_incident_comparison(comparisons: List[Dict]):
    """Display incident comparisons in a table format."""
    if not comparisons:
        st.info("No incident comparisons found")
        return
    
    for comp in comparisons:
        st.subheader(f"Incident Comparison: {comp.get('current_incident_id', 'N/A')} vs {comp.get('candidate_incident_id', 'N/A')}")
        
        # Classification
        classification = comp.get('classification', 'UNKNOWN')
        if classification == "SAME":
            st.success(f"**Classification:** {classification}")
        elif classification == "SIMILAR":
            st.warning(f"**Classification:** {classification}")
        elif classification == "DIFFERENT":
            st.error(f"**Classification:** {classification}")
        else:
            st.info(f"**Classification:** {classification}")
        
        # Comparison table
        if comp.get('matching_attributes') or comp.get('differing_attributes'):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Matching Attributes:**")
                for attr in comp.get('matching_attributes', []):
                    st.write(f"✓ {attr}")
            
            with col2:
                st.write("**Differing Attributes:**")
                for attr in comp.get('differing_attributes', []):
                    st.write(f"✗ {attr}")
        
        st.write(f"**Reasoning:** {comp.get('reasoning', 'No reasoning provided')}")
        st.divider()


def display_contradictions(contradictions: List[Dict]):
    """Display contradictions with resolution."""
    if not contradictions:
        st.info("No contradictions detected")
        return
    
    for i, contr in enumerate(contradictions):
        with st.expander(f"⚠️ Contradiction {i+1}: {contr.get('contradiction_type', 'Unknown')}", expanded=False):
            st.write(f"**Description:** {contr.get('description', 'No description')}")
            
            if contr.get('documents'):
                st.write("**Documents:**")
                for doc_id in contr['documents']:
                    st.write(f"• `{doc_id}`")
            
            if contr.get('conflicting_claims'):
                st.write("**Conflicting Claims:**")
                for claim in contr['conflicting_claims']:
                    st.write(f"• {claim}")
            
            if contr.get('resolution'):
                st.success(f"**Resolution:** {contr['resolution']}")
            
            st.write(f"**Confidence:** {contr.get('confidence', 0):.2f}")


def display_timeline(documents: List[Dict]):
    """Display chronological timeline of events."""
    if not documents:
        st.info("No timeline data available")
        return
    
    # Sort documents by date
    sorted_docs = sorted(documents, key=lambda x: x.get('date', ''))
    
    st.subheader("📅 Investigation Timeline")
    
    for doc in sorted_docs:
        date = doc.get('date', 'Unknown')
        doc_type = doc.get('document_type', 'unknown')
        title = doc.get('title', 'No title')
        doc_id = doc.get('document_id', 'N/A')
        
        # Different icons for different document types
        icon_map = {
            'incident_report': '🚨',
            'deployment_note': '🚀',
            'postmortem': '📋',
            'troubleshooting_guide': '🔧',
            'architecture_document': '🏗️'
        }
        icon = icon_map.get(doc_type, '📄')
        
        st.write(f"{icon} **{date}** - {doc_type}: {title} (`{doc_id}`)")


def display_final_report(result: Dict[str, Any]):
    """Display the final investigation report."""
    st.header("📊 Final Investigation Report")
    
    # Summary
    st.subheader("Investigation Summary")
    st.write(result.get('answer', 'No final answer available'))
    
    # Evidence Status
    col1, col2, col3 = st.columns(3)
    with col1:
        evidence_sufficient = result.get('evidence_sufficient', False)
        if evidence_sufficient:
            st.success("✅ Evidence Sufficient")
        else:
            st.warning("⚠️ Evidence Insufficient")
    
    with col2:
        st.metric("Iterations", result.get('iteration_count', 0))
    
    with col3:
        st.metric("Evidence Items", len(result.get('evidence', [])))
    
    # Evidence Gaps
    if result.get('evidence_gaps'):
        st.subheader("⚠️ Evidence Gaps")
        for gap in result['evidence_gaps']:
            st.write(f"• {gap}")
    
    # Supporting Evidence
    if result.get('evidence'):
        st.subheader("📄 Supporting Evidence")
        display_evidence(result['evidence'])
    
    # Historical Comparisons
    if result.get('related_incidents'):
        st.subheader("🔗 Historical Comparisons")
        display_incident_comparison(result['related_incidents'])
    
    # Contradictions
    if result.get('contradictions'):
        st.subheader("⚠️ Contradictions")
        display_contradictions(result['contradictions'])
    
    # Timeline
    if result.get('retrieved_documents'):
        st.subheader("📅 Timeline")
        display_timeline(result['retrieved_documents'])
    
    # Conclusion
    st.subheader("🎯 Conclusion")
    st.write(result.get('answer', 'No conclusion available'))


# Main UI
def main():
    st.title("🔍 Investigation AI")
    st.markdown("Agentic incident investigation system with traceable reasoning")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        # API URL
        api_url_input = st.text_input("API URL", API_URL)
        
        # Health check
        if st.button("Check Health"):
            health = call_api("/health")
            if health:
                st.success(f"Status: {health.get('status', 'unknown')}")
                st.info(f"PostgreSQL: {health.get('postgres', 'unknown')}")
                st.info(f"Qdrant: {health.get('qdrant', 'unknown')}")
        
        st.divider()
        st.header("Example Questions")
        example_questions = [
            "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?",
            "Investigate incident INC-1042",
            "Are there similar incidents to the catalog API latency?",
            "What caused the database connection pool exhaustion?"
        ]
        
        for q in example_questions:
            if st.button(q, key=q[:20]):
                st.session_state.question = q
    
    # Main content
    st.header("Start Investigation")
    
    # Question input
    question = st.text_area(
        "Enter your investigation question:",
        value=st.session_state.get('question', ''),
        height=100
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        start_button = st.button("🚀 Start Investigation", type="primary")
    with col2:
        clear_button = st.button("🗑️ Clear")
    
    if clear_button:
        st.session_state.clear()
        st.rerun()
    
    # Run investigation
    if start_button and question:
        with st.spinner("Investigation in progress... This may take a moment."):
            result = call_api("/investigate", method="POST", data={"question": question})
        
        if result:
            st.session_state.investigation_result = result
            st.session_state.investigation_id = result.get('investigation_id')
    
    # Display results
    if 'investigation_result' in st.session_state:
        result = st.session_state.investigation_result
        
        # Status
        status = result.get('status', 'unknown')
        if status == 'completed':
            st.success(f"✅ Investigation Complete (ID: {result.get('investigation_id', 'N/A')})")
        else:
            st.warning(f"⚠️ Investigation Status: {status}")
        
        # Investigation Trace
        st.header("🔍 Investigation Trace")
        st.markdown("Step-by-step investigation process:")
        
        trace = result.get('trace', [])
        if trace:
            for entry in trace:
                display_trace_entry(entry)
        else:
            st.info("No trace data available")
        
        # Final Report
        display_final_report(result)


if __name__ == "__main__":
    main()
