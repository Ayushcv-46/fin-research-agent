import json, os, sys, time
sys.path.insert(0, '/mnt/c/Users/ayushcv/Documents/project/fin-research-agent')
from agents.judge_agent import judge_agent_node
from agents.prompts.judge_prompt import build_judge_prompt

with open("results/analyst_outputs.json") as f:
    analyst_data = json.load(f)

NIM_PRICE_PER_1K_TOKENS = 0.0002  # adjust to your actual NIM pricing
results = {"api": [], "finetuned": []}

for entry in analyst_data["outputs"]:
    ticker, report_draft = entry["ticker"], entry["report_draft"]
    if not report_draft:
        continue
    state = {"ticker": ticker, "question": f"Risks and opportunities for {ticker}?",
              "report_draft": report_draft, "retrieved_chunks": []}

    for mode in ["api", "finetuned"]:
        os.environ["JUDGE_MODE"] = mode
        start = time.time()
        try:
            out = judge_agent_node(state)
            elapsed = time.time() - start
            full_prompt = build_judge_prompt(report_draft, state["retrieved_chunks"])
            est_tokens = len(full_prompt) // 4  # rough estimate
            cost = (est_tokens / 1000) * NIM_PRICE_PER_1K_TOKENS if mode == "api" else 0.0
            results[mode].append({"ticker": ticker, "latency_sec": round(elapsed, 2), "est_cost_usd": round(cost, 6)})
        except Exception as e:
            print(f"{mode}/{ticker} failed: {e}")
        time.sleep(3)

summary = {}
for mode in ["api", "finetuned"]:
    lat = [r["latency_sec"] for r in results[mode]]
    cost = [r["est_cost_usd"] for r in results[mode]]
    summary[mode] = {
        "avg_latency_sec": round(sum(lat)/len(lat), 2) if lat else None,
        "avg_cost_usd": round(sum(cost)/len(cost), 6) if cost else None,
        "n": len(lat)
    }

results["summary"] = summary
os.makedirs("results", exist_ok=True)
with open("results/benchmark.json", "w") as f:
    json.dump(results, f, indent=2)
print(json.dumps(summary, indent=2))