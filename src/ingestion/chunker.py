import json
import re
import os
import tiktoken
import nltk
from typing import List, Dict

# Mandatory NLTK downloads for sentence tokenization
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

def detect_section(page_text: str) -> str:
    """Return first section header found in page, or empty string."""
    if not page_text:
        return ""
    
    lines = page_text.splitlines()[:5]
    
    patterns = [
        r"^[A-Z][A-Z\s\-/]{4,}$",           # All-caps line
        r"^\d+\.(\d+\.)*\s+[A-Z]",         # Numbered heading
        r"^(I{1,3}|IV|V|VI{0,3}|IX|X)[\.\s]" # Roman numeral heading
    ]
    
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
        for pattern in patterns:
            if re.match(pattern, stripped_line):
                return stripped_line
    
    return ""

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64,
               encoding_name: str = "cl100k_base") -> List[str]:
    """Split text into overlapping chunks. Never cuts mid-sentence."""
    if not text:
        return []

    encoding = tiktoken.get_encoding(encoding_name)
    sentences = nltk.tokenize.sent_tokenize(text)
    
    chunks = []
    current_chunk_sentences = []
    current_chunk_tokens = 0
    
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        sentence_tokens = len(encoding.encode(sentence))
        
        # If adding this sentence exceeds chunk_size
        if current_chunk_tokens + sentence_tokens > chunk_size and current_chunk_sentences:
            # Save current chunk
            chunks.append(" ".join(current_chunk_sentences))
            
            # Start new chunk with overlap
            # Greedily take previous sentences for overlap
            overlap_sentences = []
            overlap_tokens = 0
            
            for prev_sent in reversed(current_chunk_sentences):
                prev_sent_tokens = len(encoding.encode(prev_sent))
                if overlap_tokens + prev_sent_tokens <= overlap:
                    overlap_sentences.insert(0, prev_sent)
                    overlap_tokens += prev_sent_tokens
                else:
                    break
            
            current_chunk_sentences = overlap_sentences
            current_chunk_tokens = overlap_tokens

            # Safety: if the sentence still can't fit even with just the overlap,
            # clear overlap so the single-oversized-sentence path (line below) can fire.
            if current_chunk_tokens + sentence_tokens > chunk_size:
                current_chunk_sentences = []
                current_chunk_tokens = 0

            continue

        # If a single sentence exceeds chunk_size and we have no current chunk
        if sentence_tokens > chunk_size and not current_chunk_sentences:
            chunks.append(sentence)
            i += 1
            continue
            
        current_chunk_sentences.append(sentence)
        current_chunk_tokens += sentence_tokens
        i += 1
        
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))
        
    return chunks

def chunk_document(pages: List[Dict], chunk_size: int = 512,
                   overlap: int = 64) -> List[Dict]:
    """Chunk all pages, return list of Chunk dicts."""
    all_chunks = []
    
    for page in pages:
        doc_id = page.get("doc_id", "unknown")
        page_num = page.get("page", 0)
        text = page.get("text", "")
        
        section_header = detect_section(text)
        text_chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        
        for idx, chunk_content in enumerate(text_chunks):
            chunk_dict = {
                "id": f"{doc_id}_p{page_num}_c{idx:03d}",
                "text": chunk_content,
                "doc_id": doc_id,
                "page": page_num,
                "section": section_header
            }
            all_chunks.append(chunk_dict)
            
    return all_chunks

def save_chunks(chunks: List[Dict], output_path: str) -> None:
    """Save chunks list as JSON to output_path."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
