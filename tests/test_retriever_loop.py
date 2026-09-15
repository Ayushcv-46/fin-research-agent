import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest.mock import patch
from agents.retriever_agent import retriever_agent_node, retry_retrieval_node

from agents.graph import build_graph


def test_retriever_returns_chunks_when_collection_populated():
    with patch("retrieval.vector_store.query_filing") as mock_query, \
         patch("retrieval.vector_store._client") as mock_client:

        mock_client.get_or_create_collection.return_value.count.return_value = 5
        mock_query.return_value = [
            {"text": "Apple's revenue grew 8%.", "section": "Item 7", "distance": 0.1}
        ]

        state = {"ticker": "AAPL", "question": "How is revenue trending?"}
        result = retriever_agent_node(state)

        assert result["retrieved_chunks"][0]["text"] == "Apple's revenue grew 8%."
        assert result["current_query"] == "How is revenue trending?"


def test_retry_retrieval_increments_count_and_reformulates():
    with patch("agents.retriever_agent.call_llm", return_value="Revised: Apple margin trends"):
        state = {
            "question": "How is Apple doing?",
            "ticker": "AAPL",
            "retrieved_chunks": [{"text": "irrelevant chunk"}],
            "confidence_reasoning": "chunks did not address the question",
            "retry_count": 0,
        }
        result = retry_retrieval_node(state)

        assert result["retry_count"] == 1
        assert result["current_query"] == "Revised: Apple margin trends"


if __name__ == "__main__":
    graph = build_graph()

    test_state = {
        "ticker": "TSLA",
        "question": "What's going on with Tesla",
    }

    result = graph.invoke(test_state)

    print("Final confidence label:", result.get("confidence_label"))
    print("Retry count:", result.get("retry_count"))
    print("Final query used:", result.get("current_query"))
    print("Report draft:", result.get("report_draft"))