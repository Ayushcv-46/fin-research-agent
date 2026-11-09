"""Small dependency-free BM25 ranker for local filing chunks."""
from collections import Counter
import math
import re


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())


def bm25_scores(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Return Okapi BM25 scores aligned with documents (higher is better)."""
    query_terms = tokenize(query)
    tokenized = [tokenize(document) for document in documents]
    if not query_terms or not tokenized:
        return [0.0] * len(documents)
    lengths = [len(document) for document in tokenized]
    avg_length = sum(lengths) / max(len(lengths), 1)
    frequencies = [Counter(document) for document in tokenized]
    scores = []
    for terms, length in zip(frequencies, lengths):
        score = 0.0
        for term in query_terms:
            df = sum(term in item for item in frequencies)
            idf = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
            tf = terms[term]
            denominator = tf + k1 * (1 - b + b * length / (avg_length or 1))
            score += idf * tf * (k1 + 1) / denominator if tf else 0.0
        scores.append(score)
    return scores


def reciprocal_rank_fusion(*ranked_lists: list[dict], limit: int, rank_constant: int = 60) -> list[dict]:
    """Fuse ranked result lists, preserving chunk metadata and rank provenance."""
    fused: dict[str, dict] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            key = item.get("id") or f"{item.get('section')}:{item.get('text')}"
            if key not in fused:
                fused[key] = {**item, "rrf_score": 0.0, "dense_rank": None, "bm25_rank": None}
            fused[key]["rrf_score"] += 1.0 / (rank_constant + rank)
            source = item.get("_rank_source")
            if source:
                fused[key][f"{source}_rank"] = rank
    return sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)[:limit]
