import json
import matplotlib.pyplot as plt
import os

os.makedirs("results/charts", exist_ok=True)

with open("results/retrieval_comparison.json") as f:
    retrieval = json.load(f)["summary"]
with open("results/judge_agreement.json") as f:
    agreement = json.load(f)
with open("results/benchmark.json") as f:
    bench = json.load(f)["summary"]

# Chart 1: fixed vs adaptive relevancy
plt.figure()
plt.bar(["Fixed", "Adaptive"], [retrieval["fixed"]["avg_answer_relevancy"], retrieval["adaptive"]["avg_answer_relevancy"]])
plt.title("Answer Relevancy: Fixed vs Adaptive Retrieval")
plt.ylabel("Avg Answer Relevancy")
plt.savefig("results/charts/retrieval_comparison.png")

# Chart 2: API vs finetuned judge scatter (overall score)
api_scores = [e["api_scores"]["overall"] for e in agreement["entries"]]
ft_scores = [e["finetuned_scores"]["overall"] for e in agreement["entries"]]

overall_corr = agreement["aggregate_stats"]["pearson_correlation"]["overall"]
correlation = overall_corr["correlation"]
p_value = overall_corr["p_value"]

plt.figure()
plt.scatter(api_scores, ft_scores)
plt.plot([0, 10], [0, 10], linestyle="--", color="gray")
plt.xlabel("API Judge Overall Score")
plt.ylabel("Finetuned Judge Overall Score")
plt.title("Judge Agreement: API vs Finetuned")
plt.text(0.5, 9.3, f"n={len(api_scores)}, r={correlation}, p={p_value}", fontsize=9)
plt.savefig("results/charts/judge_agreement_scatter.png")

# Chart 3: cost/latency
plt.figure()
modes = list(bench.keys())
plt.bar(modes, [bench[m]["avg_latency_sec"] or 0 for m in modes])
plt.title("Avg Latency by Judge Mode")
plt.ylabel("Seconds")
plt.savefig("results/charts/latency_comparison.png")

print(f"Correlation value used in Chart 2: r={correlation}, p={p_value}")
print("Charts saved to results/charts/")