import logging
import sys
import os
from app.graph.state import InvestigationState, InvestigationPlan
from app.graph.workflow import create_investigation_graph
from app.tools.tool_registry import register_default_providers
from app.config.settings import settings

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# Register default tool providers (dependency injection)
try:
    register_default_providers()
    logger.info("Default tool providers registered successfully")
except Exception as e:
    logger.error(f"Failed to register tool providers: {e}")
    logger.warning("Investigation may fail if tools are not registered")


def run_investigation(question: str) -> InvestigationState:
    """
    Run an investigation with the given question.
    """
    logger.info("=" * 60)
    logger.info("STARTING INVESTIGATION")
    logger.info("=" * 60)
    logger.info(f"Question: {question}")
    logger.info("=" * 60)
    
    # Initialize state
    initial_state: InvestigationState = {
        "question": question,
        "investigation_plan": {},  # Will be populated by Planner Agent
        "discovered_entities": [],  # Entities discovered during investigation
        "searches_performed": [],
        "retrieved_documents": [],
        "evidence": [],
        "contradictions": [],
        "related_incidents": [],
        "findings": [],
        "evidence_sufficient": False,
        "evidence_gaps": [],  # Missing evidence types
        "investigation_trace": [],  # Structured trace
        "final_answer": None,
        "iteration_count": 0
    }
    
    # Create and run the graph
    try:
        graph = create_investigation_graph()
        logger.info("Graph created successfully")
        
        # Execute the graph
        final_state = graph.invoke(initial_state)
        
        logger.info("=" * 60)
        logger.info("INVESTIGATION COMPLETED")
        logger.info("=" * 60)
        
        return final_state
        
    except Exception as e:
        logger.error(f"Error during investigation: {e}")
        raise


def main():
    """
    Main entry point for the investigation system.
    """
    # Example questions to investigate
    example_questions = [
        "What happened with the payment service in January 2024?",
        "Investigate incident INC-2024-001",
        "Are there similar incidents to the payment service outage?",
        "What caused the authentication failures in March 2024?"
    ]
    
    print("=" * 60)
    print("AGENTIC INVESTIGATION SYSTEM")
    print("=" * 60)
    print("Example questions:")
    for i, question in enumerate(example_questions, 1):
        print(f"{i}. {question}")
    print()
    
    # Get user input
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        print("Enter your investigation question (or press Enter for example):")
        user_input = input().strip()
        
        if user_input:
            question = user_input
        else:
            question = example_questions[0]  # Use first example
            print(f"Using example: {question}")
    
    print()
    
    # Run investigation
    try:
        final_state = run_investigation(question)
        
        # Print final answer
        print()
        print("=" * 60)
        print("FINAL REPORT")
        print("=" * 60)
        print(final_state["final_answer"])
        print()
        
        # Print summary statistics
        print("=" * 60)
        print("INVESTIGATION SUMMARY")
        print("=" * 60)
        print(f"Total iterations: {final_state['iteration_count']}")
        print(f"Searches performed: {len(final_state['searches_performed'])}")
        print(f"Documents retrieved: {len(final_state['retrieved_documents'])}")
        print(f"Evidence items: {len(final_state['evidence'])}")
        print(f"Contradictions found: {len(final_state['contradictions'])}")
        print(f"Related incidents: {len(final_state['related_incidents'])}")
        print(f"Evidence sufficient: {final_state['evidence_sufficient']}")
        
        # Print investigation plan summary if available
        investigation_plan = final_state.get("investigation_plan")
        if isinstance(investigation_plan, InvestigationPlan):
            print(f"Investigation objective: {investigation_plan.objective}")
            print(f"Entities identified: {len(investigation_plan.entities)}")
            print(f"Required evidence items: {len(investigation_plan.required_evidence)}")
            print(f"Investigation tasks: {len(investigation_plan.investigation_tasks)}")
        
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Failed to complete investigation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()