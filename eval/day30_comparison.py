import os
import json
import sys
from agents.graph import build_graph

def run_comparison():
    # Print which mode we are running
    current_mode = os.getenv("JUDGE_MODE", "api")
    print(f"\n{'='*50}")
    print(f"RUNNING IN JUDGE_MODE: {current_mode.upper()}")
    print(f"{'='*50}")

    graph = build_graph()
    
    # We will test on a single ticker to check schemas
    ticker = "AAPL"
    question = "What are the key risks and opportunities?"
    
    print(f"Processing Ticker: {ticker}")
    print(f"Question: {question}\n")
    
    state = graph.invoke({
        "ticker": ticker,
        "question": question,
        "current_query": question
    })
    
    # We want to see if the schemas match and output is correct
    print("--- JUDGE SCORE OUTPUT ---")
    judge_score = state.get("judge_score", {})
    print(json.dumps(judge_score, indent=2))
    print("--------------------------\n")

if __name__ == "__main__":
    run_comparison()
