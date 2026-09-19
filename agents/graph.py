import os
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from agents.data_agent import data_agent_node
from agents.retriever_agent import retriever_agent_node, retry_retrieval_node
from retrieval.confidence_scorer import confidence_scorer_node  # from Day 11
from agents.analyst_agent import analyst_agent_node
from agents.judge_agent import judge_agent_node
from agents.report_agent import report_agent_node

def route_after_confidence_check(state: dict) -> str:
    """
    Conditional edge decision function.
    In fixed mode: scoring still runs but we always proceed (never retry).
    In adaptive mode: original Day 12 retry logic applies.
    """
    # Fixed mode — ignore the confidence label, always proceed
    if os.environ.get("RETRIEVAL_MODE", "adaptive") == "fixed":
        return "proceed"

    # Adaptive mode — original retry logic
    label = state["confidence_label"]
    retries = state.get("retry_count", 0)

    if label in ("Incorrect", "Ambiguous") and retries < 2:
        return "retry_retrieval"
    return "proceed"


from typing import TypedDict

class GraphState(TypedDict, total=False):
    question: str
    ticker: str
    current_query: str
    retrieved_chunks: list
    retry_count: int
    confidence_label: str
    confidence_reasoning: str
    report_draft: dict
    judge_score: dict
    final_report: str
    price_data: dict
    fundamentals: dict
    filing_text: str
    # DEBUG: set True in tests to force Ambiguous on attempt 1 and verify retry loop
    _force_ambiguous_once: bool

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("data", data_agent_node)
    graph.add_node("retriever", retriever_agent_node)
    graph.add_node("confidence_check", confidence_scorer_node)
    graph.add_node("retry_retrieval", retry_retrieval_node)
    graph.add_node("analyst", analyst_agent_node)
    graph.add_node("judge", judge_agent_node)
    graph.add_node("report", report_agent_node)

    graph.set_entry_point("data")
    graph.add_edge("data", "retriever")
    graph.add_edge("retriever", "confidence_check")

    graph.add_conditional_edges(
        "confidence_check",
        route_after_confidence_check,
        {
            "retry_retrieval": "retry_retrieval",
            "proceed": "analyst"
        }
    )

    graph.add_edge("retry_retrieval", "retriever")

    graph.add_edge("analyst", "judge")
    graph.add_edge("judge", "report")
    graph.add_edge("report", END)

    return graph.compile()


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke({
        "ticker": "GOOGL",
        "question": "How is Alphabet's growth outlook?",
        "current_query": "How is Alphabet's growth outlook?",
    })
    print(result["final_report"])