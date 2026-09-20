import os
import time
from dotenv import load_dotenv

load_dotenv()

# Force fixed retrieval mode and API judge
os.environ["RETRIEVAL_MODE"] = "fixed"
os.environ["JUDGE_MODE"] = "api"

from agents.graph import build_graph
import retrieval.vector_store as vector_store

def run_timing(ticker: str, question: str, cold: bool):
    if cold:
        # Delete Chroma collection for this ticker if exists to simulate cold run
        coll_name = f"ticker_{ticker.lower()}"
        try:
            vector_store._client.delete_collection(name=coll_name)
            print(f"Deleted collection {coll_name} for cold run.")
        except Exception:
            pass

    graph = build_graph()
    initial_state = {
        "ticker": ticker,
        "question": question,
        "current_query": question,
        "judge_mode": "api",
        "retrieval_mode": "fixed",
    }

    print(f"\n--- Starting {'COLD' if cold else 'WARM'} run for {ticker} ---")
    start_total = time.time()
    node_timings = {}
    last_node_time = start_total

    final_state = dict(initial_state)
    for chunk in graph.stream(initial_state):
        now = time.time()
        for node_name, node_output in chunk.items():
            elapsed = now - last_node_time
            node_timings[node_name] = elapsed
            print(f"Node '{node_name}': {elapsed:.2f}s")
            last_node_time = now
            if isinstance(node_output, dict):
                final_state.update(node_output)

    total_time = time.time() - start_total
    print(f"TOTAL TIME: {total_time:.2f}s")
    print(f"Judge Score: {final_state.get('judge_score')}")
    print(f"Report Length: {len(final_state.get('final_report', ''))} chars")
    return node_timings, total_time

if __name__ == "__main__":
    q = "What are the primary drivers of revenue growth and key operational risks?"
    cold_timings, cold_total = run_timing("AAPL", q, cold=True)
    warm_timings, warm_total = run_timing("AAPL", q, cold=False)
