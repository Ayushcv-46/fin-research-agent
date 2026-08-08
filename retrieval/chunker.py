import re

def chunk_filing(text, chunk_size=512, overlap=50):
    # Step 1: Split the filing into sections using "Item X" headers
    sections = split_into_sections(text)
    
    # Step 2: Chunk each section separately
    all_chunks = []
    for section_label, section_text in sections:
        words = section_text.split()
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            all_chunks.append((chunk_text, section_label))
            start = end - overlap  # move forward, but overlap a bit
    
    return all_chunks


def split_into_sections(text):
    # Regex pattern to find headers like "Item 1A." or "Item 7."
    pattern = r"(Item\s+\d+[A-Z]?\.)"
    
    # re.split with a capturing group keeps the delimiters in the result
    parts = re.split(pattern, text)
    
    sections = []
    # parts looks like: ['...intro text...', 'Item 1.', 'text after item1', 'Item 1A.', 'text...']
    for i in range(1, len(parts), 2):
        label = parts[i].strip()          # e.g. "Item 1A."
        content = parts[i + 1].strip()    # the text belonging to that item
        sections.append((label, content))
    
    return sections