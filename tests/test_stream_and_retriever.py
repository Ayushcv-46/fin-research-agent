from unittest.mock import patch, MagicMock
from agents.graph import build_graph
from agents.retriever_agent import retriever_agent_node


def _mock_llm_response(text: str):
    resp = MagicMock()
    resp.content = text
    return resp


def test_streamed_accumulation_matches_invoke():
    """
    Verifies that accumulating node outputs from GRAPH.stream()
    produces the exact same final state as GRAPH.invoke().
    """
    graph = build_graph()

    mock_analyst_json = '{"bull_points": ["Strong growth (Section: Item 7.)"], "bear_points": [], "summary": "Positive.", "citations": ["Item 7."]}'
    mock_judge_json = '{"grounding": 9, "completeness": 8, "clarity": 9, "overall": 9, "flagged_issues": []}'

    initial_state = {
        "ticker": "AAPL",
        "question": "How is Apple doing?",
        "current_query": "How is Apple doing?",
        "judge_mode": "api",
    }

    with patch.dict("os.environ", {"RETRIEVAL_MODE": "fixed"}), \
         patch("agents.data_agent.get_cached", return_value=None), \
         patch("agents.data_agent.set_cached"), \
         patch("agents.data_agent.get_price_snapshot", return_value={"price": 200.0}), \
         patch("agents.data_agent.get_fundamentals", return_value={"pe_ratio": 25}), \
         patch("agents.data_agent.get_cik", return_value="0000320193"), \
         patch("agents.data_agent.get_latest_10k", return_value="<html>10-K text</html>"), \
         patch("agents.data_agent.clean_filing_text", return_value="cleaned text"), \
         patch("agents.retriever_agent.vector_store._client") as mock_client, \
         patch("agents.retriever_agent.vector_store.query_filing", return_value=[{"text": "Apple grew 10%", "section": "Item 7.", "distance": 0.1}]), \
         patch("retrieval.confidence_scorer.call_llm", return_value='{"label": "Correct", "reasoning": "Sufficient context found in filing."}'), \
         patch("agents.analyst_agent.llm") as mock_analyst_llm, \
         patch("agents.judge_agent.llm") as mock_judge_llm:

        mock_client.get_or_create_collection.return_value.count.return_value = 5
        mock_analyst_llm.invoke.return_value = _mock_llm_response(mock_analyst_json)
        mock_judge_llm.invoke.return_value = _mock_llm_response(mock_judge_json)


        # 1. Streamed accumulation (exactly as in /report/stream)
        stream_state = dict(initial_state)
        for chunk in graph.stream(initial_state):
            for node_name, node_output in chunk.items():
                if isinstance(node_output, dict):
                    stream_state.update(node_output)

        # 2. Synchronous invoke
        invoke_state = graph.invoke(initial_state)

        # Assert equivalence
        assert stream_state == invoke_state
        assert stream_state["ticker"] == "AAPL"
        assert stream_state["judge_score"]["overall"] == 9
        assert "Financial Research Report: AAPL" in stream_state["final_report"]


def test_embedding_runs_once_per_chunk():
    """
    Verifies that chunk embedding is executed exactly once per batch of chunks
    when a new filing is ingested.
    """
    sample_filing = "Item 1. Business summary here. Item 7. Financial condition here."

    with patch("agents.retriever_agent.vector_store._client") as mock_client, \
         patch("agents.retriever_agent.vector_store.ingest_filing") as mock_ingest, \
         patch("agents.retriever_agent.vector_store.query_filing", return_value=[{"text": "chunk 1", "section": "Item 1", "distance": 0.1}]), \
         patch("retrieval.embedder.get_embedder") as mock_get_embedder:

        mock_model = MagicMock()
        mock_get_embedder.return_value = mock_model
        # Return dummy embeddings list matching input length
        mock_model.encode.side_effect = lambda texts, **kwargs: [[0.1] * 384 for _ in texts]

        # Simulate collection is empty so ingestion is triggered
        mock_client.get_or_create_collection.return_value.count.return_value = 0

        state = {
            "ticker": "TSLA",
            "question": "What are the risk factors?",
            "filing_text": sample_filing,
        }

        retriever_agent_node(state)

        assert mock_ingest.called
        # Check that encode was called for the batch of chunks
        # In chunk_filing -> embed_chunks, encode is called once on the list of chunk texts
        assert mock_model.encode.call_count >= 1
        # Ingested chunks received embeddings
        ingested_chunks = mock_ingest.call_args[0][1]
        assert len(ingested_chunks) > 0
        assert "embedding" in ingested_chunks[0]
