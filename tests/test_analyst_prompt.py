# test_analyst_prompt.py
# Throwaway manual test script for Day 13 — NOT part of the final project structure.
# Goal: manually test the Analyst prompt on a real ticker before wiring it into
# analyst_agent_node tomorrow (Day 14).

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.market_data import get_fundamentals
from data.edgar_fetcher import get_cik, get_latest_10k, clean_filing_text
from retrieval.chunker import chunk_filing
from retrieval.vector_store import ingest_filing, query_filing
from agents.prompts.analyst_prompt import build_analyst_prompt

from agents.llm_client import call_llm


# --- CHANGE THIS to test different companies ---
ticker = "AAPL"

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
    section_filter="Item 7."
)
risk_chunks = query_filing(
    ticker,
    "What are the company's main risks and challenges?",
    top_k=3,
    section_filter="Item 1A."
)
retrieved_chunks = growth_chunks + risk_chunks
print(f"\nRetrieved {len(retrieved_chunks)} chunks total (growth + risk)\n")

# retrieved_chunks should look like: [{"text": "...", "section": "Item 7"}, ...]
# adjust the key names below if your query_filing() returns a different shape

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

# 8. Manual checklist reminder
print("\nManual check:")
print("- Does every Bull/Bear point have a (Section: ...) citation?")
print("- Is every citation actually traceable to a retrieved chunk?")
print("- Is there any buy/sell language? (should be NONE)")
print("- Are all 3 headings present: BULL CASE / BEAR CASE / SUMMARY?")