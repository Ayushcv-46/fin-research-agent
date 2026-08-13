from langgraph.graph import StateGraph, END
from agents.data_agents import data_agent_node, GraphState
from agents.retriever_agent import retriever_agent_node

graph = StateGraph(GraphState)

graph.add_node("data_agent", data_agent_node)
graph.add_node("retriever_agent", retriever_agent_node)

graph.set_entry_point("data_agent")
graph.add_edge("data_agent", "retriever_agent")
graph.add_edge("retriever_agent", END)

app = graph.compile()

if __name__ == "__main__":
    initial_state = {
        "ticker": "AAPL",
        "question": "What are the main risks mentioned in the filing?"
    }

    result = app.invoke(initial_state)

    print(f"Retrieved {len(result['retrieved_chunks'])} chunks:")
    for chunk in result["retrieved_chunks"]:
        print(chunk["section"], "-", chunk["text"][:100])