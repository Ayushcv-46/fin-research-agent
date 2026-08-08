from sentence_transformers import SentenceTransformer

# Load the pre-trained model once — reused from your RAG chatbot project
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_chunks(chunks):
    # chunks is a list of (chunk_text, section_label) tuples from chunker.py
    texts = [chunk_text for chunk_text, section_label in chunks]
    
    # This is the actual embedding step — turns each string into a vector
    embeddings = model.encode(texts)
    
    # Zip everything back together: text, label, embedding
    result = []
    for (chunk_text, section_label), embedding in zip(chunks, embeddings):
        result.append((chunk_text, section_label, embedding))
    
    return result