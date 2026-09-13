import json
import os
import sys
import time

sys.path.insert(0, '/mnt/c/Users/ayushcv/Documents/project/fin-research-agent')

from agents.graph import build_graph

GRAPH = build_graph()

TICKERS = ["AAPL", "TSLA", "NFLX", "GOOGL", "META", "AMZN", "MSFT", "NVDA", "WMT", "PFE", "DIS", "XOM"]
ANALYST_OUTPUT_PATH = "/mnt/c/Users/ayushcv/Documents/project/fin-research-agent/results/analyst_outputs.json"

def prepare_analyst_outputs():
    """Run analyst for all 12 tickers, save report_draft to JSON."""
    
    # Load existing or start fresh
    if os.path.exists(ANALYST_OUTPUT_PATH):
        with open(ANALYST_OUTPUT_PATH, "r") as f:
            data = json.load(f)
        print(f"Loaded {len(data['outputs'])} existing entries")
    else:
        data = {"outputs": []}
    
    processed = {entry["ticker"] for entry in data["outputs"]}
    
    for ticker in TICKERS:
        if ticker in processed:
            print(f"✓ {ticker} already processed — skipping")
            continue
        
        print(f"\nAnalyzing {ticker}...")
        try:
            state = GRAPH.invoke({
                "ticker": ticker,
                "question": f"What are the main risks and growth opportunities for {ticker}?"
            })
            
            report_draft = state.get("report_draft", {})
            
            entry = {
                "ticker": ticker,
                "report_draft": report_draft
            }
            
            data["outputs"].append(entry)
            
            with open(ANALYST_OUTPUT_PATH, "w") as f:
                json.dump(data, f, indent=2)
            
            print(f"  ✓ Saved {ticker}")
        
        except Exception as e:
            print(f"  ✗ Error on {ticker}: {e}")
        
        time.sleep(5)
    
    print(f"\n✓ All analyst outputs saved to {ANALYST_OUTPUT_PATH}")

if __name__ == "__main__":
    prepare_analyst_outputs()