import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Data.edgar_fetcher import get_cik, get_latest_10k, clean_filing_text

ticker = "TSLA"

cik = get_cik(ticker)
print(f"CIK for {ticker}: {cik}")

html = get_latest_10k(cik)
print(f"Downloaded filing, raw length: {len(html)} characters")

text = clean_filing_text(html)
print(f"Cleaned length: {len(text)} characters")
print("--- First 500 characters ---")
print(text[:500])