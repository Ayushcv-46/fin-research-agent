import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.graph import build_graph

graph = build_graph()

test_state = {
    "ticker": "TSLA",
    "question": "What's going on with Tesla",
}

result = graph.invoke(test_state)

print("Final confidence label:", result.get("confidence_label"))
print("Retry count:", result.get("retry_count"))
print("Final query used:", result.get("current_query"))
print("Report draft:", result.get("report_draft"))
