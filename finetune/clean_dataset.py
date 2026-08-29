# finetune/clean_dataset.py
import json
import random
from collections import defaultdict

def load_raw(path="finetune/dataset_raw.jsonl"):
    rows = []
    with open(path) as f:
        for line in f:
            rows.append(json.loads(line))
    return rows

def validate_row(row: dict) -> bool:
    if not all(k in row for k in ("instruction", "input", "output")):
        return False
    try:
        output = json.loads(row["output"])
    except json.JSONDecodeError:
        return False
    required_keys = {"grounding", "completeness", "clarity", "overall", "flagged_issues"}
    if not required_keys.issubset(output.keys()):
        return False
    if output["grounding"] == -1:
        return False
    return True

def deduplicate(rows: list[dict]) -> list[dict]:
    seen, unique = set(), []
    for r in rows:
        key = r["input"]  # identical input = duplicate example
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

def group_by_ticker(rows: list[dict]) -> dict:
    corrupted = [r for r in rows if "_ticker" in r]
    good = [r for r in rows if "_ticker" not in r]

    groups = defaultdict(list)
    used_good_indices = set()

    for c_row in corrupted:
        ticker = c_row["_ticker"]
        best_match_idx, best_overlap = None, 0
        for i, g_row in enumerate(good):
            if i in used_good_indices:
                continue
            overlap = len(set(g_row["input"].split()) & set(c_row["input"].split()))
            if overlap > best_overlap:
                best_overlap, best_match_idx = overlap, i

        groups[ticker].append(c_row)
        if best_match_idx is not None:
            groups[ticker].append(good[best_match_idx])
            used_good_indices.add(best_match_idx)

    for i, g_row in enumerate(good):
        if i not in used_good_indices:
            groups[f"solo_{i}"].append(g_row)

    return groups

def split_groups(groups: dict, val_ratio=0.15, seed=42):
    group_keys = list(groups.keys())
    random.seed(seed)
    random.shuffle(group_keys)

    val_count = max(1, int(len(group_keys) * val_ratio))
    val_keys = set(group_keys[:val_count])

    train_rows, val_rows = [], []
    for key, rows in groups.items():
        target = val_rows if key in val_keys else train_rows
        target.extend(rows)

    return train_rows, val_rows

def strip_debug_fields(row: dict) -> dict:
    """Remove _ticker/_corruption_type before saving final train/val files."""
    return {k: v for k, v in row.items() if not k.startswith("_")}

def main():
    raw = load_raw()
    print(f"Loaded {len(raw)} raw rows")

    valid = [r for r in raw if validate_row(r)]
    print(f"{len(valid)} rows passed validation ({len(raw) - len(valid)} dropped)")

    unique = deduplicate(valid)
    print(f"{len(unique)} rows after deduplication ({len(valid) - len(unique)} duplicates removed)")

    groups = group_by_ticker(unique)
    print(f"Grouped into {len(groups)} ticker-groups")

    train_rows, val_rows = split_groups(groups)
    train_rows = [strip_debug_fields(r) for r in train_rows]
    val_rows = [strip_debug_fields(r) for r in val_rows]

    with open("finetune/train.jsonl", "w") as f:
        for r in train_rows:
            f.write(json.dumps(r) + "\n")
    with open("finetune/val.jsonl", "w") as f:
        for r in val_rows:
            f.write(json.dumps(r) + "\n")

    print(f"\nSaved {len(train_rows)} rows to train.jsonl")
    print(f"Saved {len(val_rows)} rows to val.jsonl")

if __name__ == "__main__":
    main()