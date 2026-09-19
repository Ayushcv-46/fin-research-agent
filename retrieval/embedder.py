"""
retrieval/embedder.py

Provides embedding generation using SentenceTransformer with lazy loading,
LRU caching, and an explicit warm-up hook for application startup.
"""
from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedder():
    """Lazily loads and caches the SentenceTransformer model instance."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer('all-MiniLM-L6-v2')


def warm_up_embedder() -> None:
    """Pre-loads the SentenceTransformer model into memory (e.g. at server startup)."""
    get_embedder()


def embed_text(text: str) -> list[float]:
    """
    Embed a single string into a list of floats (vector).
    """
    model = get_embedder()
    embedding = model.encode(text)
    return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)


def embed_chunks(chunks):
    if not chunks:
        return []

    is_dict = isinstance(chunks[0], dict)
    if is_dict:
        texts = [c["text"] for c in chunks]
    else:
        texts = [chunk_text for chunk_text, section_label in chunks]

    model = get_embedder()
    embeddings = model.encode(texts)

    result = []
    for chunk, embedding in zip(chunks, embeddings):
        emb_list = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
        if is_dict:
            c_copy = dict(chunk)
            c_copy["embedding"] = emb_list
            result.append(c_copy)
        else:
            chunk_text, section_label = chunk
            result.append((chunk_text, section_label, emb_list))

    return result