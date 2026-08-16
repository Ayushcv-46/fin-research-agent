from retrieval.vector_store import query_filing
from agents.llm_client import call_llm  # shared LLM client


def retriever_agent_node(state: dict) -> dict:
    """
    Searches ChromaDB for the current query (original on first run,
    reformulated on retries). Only job: search and return chunks.
    """
    ticker = state["ticker"]
    query = state.get("current_query", state["question"])

    from retrieval.vector_store import query_filing, _client, ingest_filing
    from retrieval.chunker import chunk_filing
    from retrieval.embedder import embed_chunks

    collection = _client.get_or_create_collection(name=ticker)
    if collection.count() == 0:
        print(f"[retriever_agent] Collection for {ticker} is empty. Ingesting...")
        if not state.get("filing_text"):
            from agents.data_agent import data_agent_node
            state = data_agent_node(state)  # populate filing_text
        
        filing_text = state.get("filing_text")
        if filing_text:
            raw_chunks = chunk_filing(filing_text)
            embedded_chunks = embed_chunks(raw_chunks)
            ingest_filing(ticker, embedded_chunks)
        else:
            print(f"[retriever_agent] Failed to obtain filing_text for ingestion for {ticker}.")

    chunks = query_filing(ticker, query, top_k=5)

    return {
        "retrieved_chunks": chunks,
        "current_query": query
    }


def reformulate_query(question: str, ticker: str, chunks_so_far: list, reasoning: str = "") -> str:
    """
    Rewrites the question so a fresh ChromaDB search targets
    different/missing information, instead of repeating the same search.
    """
    # Safely extract text from chunk dicts
    chunk_texts = [c.get("text", "") for c in chunks_so_far if isinstance(c, dict)]
    chunk_preview = "\n".join(t[:200] for t in chunk_texts)  # trim for prompt size
    
    prompt = f"""
    You are an expert financial research assistant.
    We are researching the company {ticker}.
    Original question: {question}
    Chunks retrieved so far (judged insufficient):
    {chunk_preview}
    Reason retrieval was insufficient: {reasoning}

    Rewrite the question to be more specific or target missing information about {ticker},
    so a new search in the company's 10-K filing is likely to find better matching content.
    Return ONLY the rewritten question, nothing else. Do not use placeholders like [industry/project/task].
    """
    response = call_llm(prompt)
    return response.strip()


def retry_retrieval_node(state: dict) -> dict:
    """
    Prepares a better query for the next retrieval attempt.
    Does NOT search itself — only reformulates + increments retry count.
    """
    new_query = reformulate_query(
        state["question"],
        state["ticker"],
        state.get("retrieved_chunks", []),
        state.get("confidence_reasoning", "")
    )
    return {
        "current_query": new_query,
        "retry_count": state.get("retry_count", 0) + 1
    }