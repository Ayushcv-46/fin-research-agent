from sentence_transformers import SentenceTransformer

# Load the pre-trained model once
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_text(text: str) -> list[float]:
    """
    Embed a single string into a list of floats (vector).
    """
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
    
    # This is the actual embedding step — turns each string into a vector
    embeddings = model.encode(texts)
    
    # Zip everything back together
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