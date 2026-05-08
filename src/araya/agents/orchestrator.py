import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END

from araya.agents.state import ResearchState
from araya.agents.lead_agent import LeadResearchAgent
from araya.agents.search_agent import SearchAgent
from araya.agents.document_analyst_agent import DocumentAnalystAgent
from araya.agents.cross_reference_agent import run_cross_reference
from araya.eval.evaluator import run_evaluation_loop
from araya.core.observability import instrument_node

logger = logging.getLogger(__name__)


def create_research_graph():
    lead_agent = LeadResearchAgent()
    search_agent = SearchAgent()
    document_analyst = DocumentAnalystAgent()

    workflow = StateGraph(ResearchState)

    workflow.add_node("plan", instrument_node("planning")(lead_agent.plan))
    workflow.add_node("search", instrument_node("searching")(search_agent.run))
    workflow.add_node("document_analysis", instrument_node("document_analysis")(document_analyst.run))
    workflow.add_node("cross_reference", instrument_node("cross_reference")(run_cross_reference))
    workflow.add_node("synthesize", instrument_node("synthesis")(lead_agent.synthesize))
    workflow.add_node("evaluate", instrument_node("evaluation")(run_evaluation_loop))

    workflow.set_entry_point("plan")

    # Fan-out from plan to both search and document_analysis
    workflow.add_edge("plan", "search")
    workflow.add_edge("plan", "document_analysis")

    # Both converge to cross_reference
    workflow.add_edge("search", "cross_reference")
    workflow.add_edge("document_analysis", "cross_reference")

    # Cross-reference -> synthesis -> evaluation
    workflow.add_edge("cross_reference", "synthesize")
    workflow.add_edge("synthesize", "evaluate")

    # Conditional: evaluate -> END (pass) or plan (fail with feedback)
    def should_continue(state: ResearchState):
        evaluation = state.get("evaluation")
        if evaluation and evaluation.passed:
            return END
        if state.get("iteration_count", 0) >= 3:
            logger.warning("Max iterations reached. Ending.")
            return END
        return "plan"

    workflow.add_conditional_edges("evaluate", should_continue)

    return workflow.compile()


research_engine = create_research_graph()
