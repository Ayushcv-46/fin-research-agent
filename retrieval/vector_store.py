"""Persistent Chroma storage with dense, BM25, and rank-fused retrieval."""
import hashlib
import re

import chromadb

from retrieval.bm25 import bm25_scores, reciprocal_rank_fusion
from retrieval.embedder import embed_text

_client = chromadb.PersistentClient(path="./chroma_db")


def _collection_name(ticker: str, filing_id: str | None = None) -> str:
    if not filing_id:
        return f"ticker_{ticker.lower()}"  # compatibility with existing indexes
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "", filing_id)
    suffix = hashlib.sha1(filing_id.encode()).hexdigest()[:8]
    return f"ticker_{ticker.lower()}_{normalized[-24:]}_{suffix}".lower()


def collection_exists(ticker: str, filing_id: str | None = None) -> bool:
    return _collection_name(ticker, filing_id) in [c.name for c in _client.list_collections()]


def ingest_filing(ticker: str, chunks: list[dict], filing_id: str | None = None,
                  filing_metadata: dict | None = None) -> None:
    """Add chunks once to a filing-specific collection; old ticker collections remain readable."""
    collection = _client.get_or_create_collection(name=_collection_name(ticker, filing_id))
    if collection.count() > 0:
        return
    collection.add(
        ids=[str(c.get("id", f"chunk_{i}")) for i, c in enumerate(chunks)],
        documents=[c["text"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        metadatas=[{"section": c.get("section", "Unknown"),
                    "filing_id": filing_id or "legacy",
                    "accession_number": (filing_metadata or {}).get("accession_number") or "unknown",
                    "filing_date": (filing_metadata or {}).get("filing_date") or "unknown",
                    "report_date": (filing_metadata or {}).get("report_date") or "unknown"}
                   for c in chunks],
    )


def _fetch(ticker: str, query: str, limit: int, section_filter: str | None,
           filing_id: str | None) -> tuple[list[dict], list[dict]]:
    collection = _client.get_or_create_collection(name=_collection_name(ticker, filing_id))
    if collection.count() == 0:
        return [], []
    count = collection.count()
    where = {"section": section_filter} if section_filter else None
    dense_raw = collection.query(query_embeddings=[embed_text(query)], n_results=min(limit, count), where=where)
    dense = []
    for chunk_id, doc, meta, distance in zip(dense_raw["ids"][0], dense_raw["documents"][0], dense_raw["metadatas"][0], dense_raw["distances"][0]):
        dense.append({"id": chunk_id, "text": doc, **meta, "distance": distance, "_rank_source": "dense"})
    # BM25 scans local documents; fetch all records to retain corpus-wide IDF statistics.
    records = collection.get(where=where, include=["documents", "metadatas"])
    scores = bm25_scores(query, records["documents"])
    bm25 = []
    for idx in sorted(range(len(scores)), key=scores.__getitem__, reverse=True)[:limit]:
        if scores[idx] <= 0:
            continue
        bm25.append({"id": records["ids"][idx], "text": records["documents"][idx],
                     **records["metadatas"][idx], "bm25_score": scores[idx], "_rank_source": "bm25"})
    return dense, bm25


def query_filing(ticker: str, query: str, top_k: int = 5,
                 section_filter: str | None = None, search_mode: str = "dense",
                 filing_id: str | None = None) -> list[dict]:
    if search_mode not in {"dense", "bm25", "hybrid"}:
        raise ValueError("search_mode must be one of: dense, bm25, hybrid")
    dense, bm25 = _fetch(ticker, query, top_k if search_mode != "hybrid" else max(20, top_k), section_filter, filing_id)
    if search_mode == "dense":
        results = dense[:top_k]
    elif search_mode == "bm25":
        results = bm25[:top_k]
    else:
        results = reciprocal_rank_fusion(dense, bm25, limit=top_k)
    for item in results:
        item.pop("_rank_source", None)
    return results
