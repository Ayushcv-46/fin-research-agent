# finetune/generate_dataset.py
import json, random, copy, time
from collections import Counter
from agents.graph import build_graph
from agents.judge_agent import judge_agent_node
from agents.prompts.judge_prompt import build_judge_prompt

GRAPH = build_graph()

def run_pipeline(ticker: str) -> dict:
    question = f"How is {ticker}'s growth outlook?"
    return GRAPH.invoke({
        "ticker": ticker,
        "question": question,
        "current_query": question,
    })

INSTRUCTION_TEXT = """You are a financial report quality judge. Score the following analyst
report using this rubric. Each criterion is scored 1-10. Overall score is
the average of the three, unless one criterion scores 1-3, in which case
overall should not exceed 5.

1. GROUNDING — Does every claim trace back to explicit language in its
cited chunk (not implied, not adjacent, not a reasonable inference)?
1-3: Claims reference chunks that don't support them, wrong-section
citations, or fabricated/garbled facts presented as real.
4-7: Right area but overstates, adds unstated framing, or blurs a risk
into a positive without contradicting the source.
8-10: Every claim directly traceable to explicit chunk language.

2. COMPLETENESS — Does the report cover what actually matters in the
filing, without padding or omitting a major risk/strength?
1-3: Missing an obviously major risk/opportunity, or generic boilerplate
points.
4-7: Real substance but thin, or one boilerplate point mixed in.
8-10: Every major theme present in the chunks is represented, no filler.

3. CLARITY — Is it organized, unambiguous, and readable on first pass?
1-3: Rambling, contradictory, unclear claim-to-citation mapping.
4-7: Readable but clunky or ambiguous mapping.
8-10: Clean and immediately understandable.

Return JSON: {"grounding": int, "completeness": int, "clarity": int,
"overall": int, "flagged_issues": [str]}"""

TICKERS = ["AMGN", "BA", "F", "CAT", "GE", "MMM", "TXT", "DE", "LMT", "RTX", 
           "GD", "HON", "UPS", "FDX", "UNP", "NEE", "DUK", "SO", "EXC", 
           "SRE", "AEP", "VZ", "T", "TMUS", "DIS", "CMCSA"]

def corrupt_report(report_draft: dict):
    """Apply ONE random, controlled corruption to a good report draft."""
    corrupted = copy.deepcopy(report_draft)
    corruption_type = random.choice(["remove_citation", "swap_number", "drop_bear_case"])

    if corruption_type == "remove_citation":
        import re
        if corrupted.get("bull_points"):
            idx = random.randrange(len(corrupted["bull_points"]))
            corrupted["bull_points"][idx] = re.sub(r'\(Section:[^\)]+\)', '', corrupted["bull_points"][idx]).strip()
    elif corruption_type == "swap_number":
        candidates = []
        if corrupted.get("bull_points"):
            candidates.extend(("bull_points", i) for i in range(len(corrupted["bull_points"])))
        if corrupted.get("bear_points"):
            candidates.extend(("bear_points", i) for i in range(len(corrupted["bear_points"])))
        
        if candidates:
            list_key, idx = random.choice(candidates)
            pt = corrupted[list_key][idx]
            if "14%" in pt:
                corrupted[list_key][idx] = pt.replace("14%", "41%")
            else:
                corrupted[list_key][idx] = pt + " [NOTE: figure deliberately altered for training]"
    elif corruption_type == "drop_bear_case":
        corrupted["bear_points"] = []

    return corrupted, corruption_type

def make_training_row(report_draft, chunks, ticker, corruption_type=None):
    judge_input = build_judge_prompt(report_draft, chunks)
    
    judge_score = {}
    for attempt in range(3):
        judge_node_result = judge_agent_node({
            "report_draft": report_draft,
            "retrieved_chunks": chunks
        })
        judge_score = judge_node_result.get("judge_score", {})
        if judge_score.get("grounding") != -1:
            break
        print(f"[{ticker}] Judge call hit sentinel (-1). Retrying ({attempt+1}/3)...")
        if attempt < 2:
            time.sleep(5)
    
    if judge_score.get("grounding") == -1:
        print(f"WARNING: {ticker} failed all 3 judge attempts, keeping sentinel score.")
        
    row = {
        "instruction": INSTRUCTION_TEXT,
        "input": judge_input,
        "output": json.dumps(judge_score),
        "_ticker": ticker
    }
    if corruption_type:
        row["_corruption_type"] = corruption_type
    return row

def main():
    rows = []
    failures = []

    for ticker in TICKERS:
        try:
            state = run_pipeline(ticker)
        except Exception as e:
            failures.append((ticker, str(e)))
            continue
            
        time.sleep(2)

        good_row = make_training_row(state["report_draft"], state["retrieved_chunks"], ticker)
        rows.append(good_row)

        if random.random() < 0.7:
            bad_draft, corruption_type = corrupt_report(state["report_draft"])
            bad_row = make_training_row(bad_draft, state["retrieved_chunks"], ticker, corruption_type)
            rows.append(bad_row)

    with open("finetune/dataset_raw.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    pairs = [(r["_ticker"], r["_corruption_type"]) for r in rows if "_corruption_type" in r]
    print(f"\nSaved {len(rows)} total rows ({len(rows) - len(pairs)} good, {len(pairs)} corrupted)")
    print("Corruption type breakdown:", Counter(t for _, t in pairs))
    if failures:
        print(f"\n{len(failures)} tickers failed and were skipped:")
        for t, err in failures:
            print(f"  {t}: {err}")

if __name__ == "__main__":
    main()