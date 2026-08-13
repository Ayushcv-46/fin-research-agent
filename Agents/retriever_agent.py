from retrieval.vector_store import collection_exists, ingest_filing, query_filing
from retrieval.chunker import chunk_filing
from retrieval.embedder import embed_chunks


def ensure_filing_ingested(state):
    ticker = state["ticker"]
    if not collection_exists(ticker):
        chunks = chunk_filing(state["filing_text"])
        embeddings = embed_chunks(chunks)
        ingest_filing(ticker, chunks, embeddings)


def retriever_agent_node(state):
    ensure_filing_ingested(state)

    question = state["question"]
    ticker = state["ticker"]

    chunks = query_filing(ticker, question, top_k=5)

    state["retrieved_chunks"] = chunks
    return state