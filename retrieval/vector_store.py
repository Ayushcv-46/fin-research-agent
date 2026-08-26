"""
retrieval/vector_store.py

Wraps ChromaDB to provide a persistent, per-ticker searchable store
for 10-K filing chunks. Used by the Retriever Agent (Day 9+).

Design:
- One Chroma collection per ticker (isolation boundary, no leakage across companies)
- ingest_filing() is idempotent — skips re-ingestion if the collection already has data
- query_filing() unwraps Chroma's nested response into a clean list[dict]
  so callers never touch ChromaDB's raw API shape
"""

import chromadb
from retrieval.embedder import embed_text  # reuse Day 7's embedder

# Single persistent client for the whole app — writes to ./chroma_db on disk
_client = chromadb.PersistentClient(path="./chroma_db")


def collection_exists(ticker: str) -> bool:
    collection_name = f"ticker_{ticker.lower()}"
    existing = [c.name for c in _client.list_collections()]
    return collection_name in existing


def ingest_filing(ticker: str, chunks: list[dict]) -> None:
    """
    Ingest a list of chunk dicts into the ticker's ChromaDB collection.

    chunks: list of {"text": str, "section": str, "embedding": list[float]}
    (this is the shape produced by Day 7's chunker + embedder)

    Idempotent: if the collection already has entries, does nothing.
    """
    collection_name = f"ticker_{ticker.lower()}"
    collection = _client.get_or_create_collection(name=collection_name)

    if collection.count() > 0:
        print(f"[ingest_filing] '{ticker}' already ingested ({collection.count()} chunks) — skipping.")
        return

    collection.add(
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        metadatas=[{"section": c["section"]} for c in chunks],
    )
    print(f"[ingest_filing] Ingested {len(chunks)} chunks for '{ticker}'.")


def query_filing(
    ticker: str,
    query: str,
    top_k: int = 5,
    section_filter: str | None = None,
) -> list[dict]:
    """
    Search a ticker's filing for chunks relevant to `query`.

    Returns a clean list of dicts (Chroma's nested response shape is
    unwrapped here so callers never deal with it):
        [{"text": str, "section": str, "distance": float}, ...]
    sorted by relevance (lowest distance = most similar, first).
    """
    collection_name = f"ticker_{ticker.lower()}"
    collection = _client.get_or_create_collection(name=collection_name)

    query_embedding = embed_text(query)  # same model as chunk embeddings — required

    where_clause = {"section": section_filter} if section_filter else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_clause,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {"text": doc, "section": meta["section"], "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]