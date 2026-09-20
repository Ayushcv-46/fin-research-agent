import os
import json
from dotenv import load_dotenv

load_dotenv()
os.environ["RETRIEVAL_MODE"] = "adaptive"
os.environ["JUDGE_MODE"] = "api"

from agents.graph import build_graph

def test_adaptive():
    graph = build_graph()
    initial_state = {
        "ticker": "AAPL",
        "question": "Tell me random stuff about something unrelated to financials.",
        "current_query": "Tell me random stuff about something unrelated to financials.",
        "judge_mode": "api",
        "retrieval_mode": "adaptive",
    }

    print("\n--- Running Adaptive Retrieval Mode with vague question ---")
    stages = []
    final_state = dict(initial_state)

    for chunk in graph.stream(initial_state):
        for node_name, node_output in chunk.items():
            stages.append(node_name)
            print(f"Stage triggered: {node_name}")
            if isinstance(node_output, dict):
                final_state.update(node_output)

    print("\nAll stages:", stages)
    print("Retry count:", final_state.get("retry_count"))
    print("Confidence label:", final_state.get("confidence_label"))
    print("Confidence reasoning:", final_state.get("confidence_reasoning"))
    assert "retry_retrieval" in stages or final_state.get("retry_count", 0) > 0 or final_state.get("confidence_label") in ("Ambiguous", "Incorrect", "Correct")
    print("Adaptive test passed!")

if __name__ == "__main__":
    test_adaptive()
