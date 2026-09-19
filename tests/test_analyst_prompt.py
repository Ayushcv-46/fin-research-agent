# test_analyst_prompt.py
# Manual test script for Day 13.
# Wrapped in main() so pytest does not execute top-level network calls on discovery.

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.market_data import get_fundamentals
from data.edgar_fetcher import get_cik, get_latest_10k, clean_filing_text
from retrieval.chunker import chunk_filing
from retrieval.vector_store import ingest_filing, query_filing
from agents.prompts.analyst_prompt import build_analyst_prompt
from agents.llm_client import call_llm


def run_manual_analyst_prompt(ticker: str = "AAPL"):
    print(f"Testing Analyst prompt for ticker: {ticker}\n")

    # 1. Get fundamentals (Day 3)
    fundamentals = get_fundamentals(ticker)
    print("Fundamentals fetched:", fundamentals)

    # 2. Get filing text (Day 4) — skip if you've already ingested this ticker before
    cik = get_cik(ticker)
    raw_html = get_latest_10k(cik)
    filing_text = clean_filing_text(raw_html)

    # 3. Chunk the filing (Day 7)
    chunks_with_embeddings = chunk_filing(filing_text)

    # 4. Ingest into ChromaDB if not already done (Day 8)
    ingest_filing(ticker, chunks_with_embeddings)

    # 5. Query for relevant chunks — use a real research question (Day 8-12)
    growth_chunks = query_filing(
        ticker,
        "What are the company's revenue growth drivers, strategic strengths, and competitive advantages?",
        top_k=3,
        section_filter="Item 7.",
    )
    risk_chunks = query_filing(
        ticker,
        "What are the company's main risks and challenges?",
        top_k=3,
        section_filter="Item 1A.",
    )
    retrieved_chunks = growth_chunks + risk_chunks
    print(f"\nRetrieved {len(retrieved_chunks)} chunks total (growth + risk)\n")

    # 6. Build the Analyst prompt (Day 13 — today's actual work)
    prompt = build_analyst_prompt(fundamentals, retrieved_chunks)

    print("----- PROMPT SENT TO LLM -----")
    print(prompt)
    print("-------------------------------\n")

    # 7. Call the LLM
    response = call_llm(prompt)

    print("----- LLM RESPONSE -----")
    print(response)
    print("-------------------------")


if __name__ == "__main__":
    run_manual_analyst_prompt("AAPL")