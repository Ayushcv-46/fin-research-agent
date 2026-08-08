import sys
import os

# Add the project root to sys.path so it can find the 'data' and 'retrieval' modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.edgar_fetcher import get_cik, get_latest_10k, clean_filing_text
# pyrefly: ignore [missing-import]
from retrieval.chunker import chunk_filing
# pyrefly: ignore [missing-import]
from retrieval.embedder import embed_chunks

cik = get_cik("AAPL")
raw_html = get_latest_10k(cik)
clean_text = clean_filing_text(raw_html)

chunks = chunk_filing(clean_text)
print(f"Number of chunks: {len(chunks)}")
print(chunks[0])  # peek at the first chunk

embedded = embed_chunks(chunks)
print(f"Embedding shape: {embedded[0][2].shape}")  # should be (384,)