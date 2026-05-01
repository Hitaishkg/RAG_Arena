import os
import json
import pdfplumber
import re
from typing import List, Dict

def extract_pages(pdf_path: str, doc_id: str) -> List[Dict]:
    """
    Opens pdf_path with pdfplumber, extracts text from each page.
    Returns list of page dicts:
      {doc_id: str, page: int, text: str, char_count: int}
    Skips pages with fewer than 50 characters (blank/header-only pages).
    """
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue
                
                # Normalise whitespace: collapse multiple newlines to single newline, strip
                text = re.sub(r'\n+', '\n', text).strip()
                
                char_count = len(text)
                if char_count < 50:
                    continue
                
                pages.append({
                    "doc_id": doc_id,
                    "page": i,
                    "text": text,
                    "char_count": char_count
                })
    except Exception as e:
        # Task says: "Handle PDF open errors with try/except, log and skip"
        # Calling function handles logging/skipping
        raise e
        
    return pages

def extract_corpus(raw_dir: str = "data/raw", processed_dir: str = "data/processed") -> None:
    """
    For each <doc_id>.pdf in raw_dir:
      - Call extract_pages()
      - Save output as data/processed/<doc_id>.json (list of page dicts)
      - Print: "Extracted <doc_id>: <N> pages, <total_chars> chars"
    Skips doc_ids already in processed_dir.
    """
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir, exist_ok=True)
        
    for filename in os.listdir(raw_dir):
        if not filename.endswith(".pdf"):
            continue
            
        doc_id = filename[:-4]
        output_path = os.path.join(processed_dir, f"{doc_id}.json")
        
        if os.path.exists(output_path):
            continue
            
        pdf_path = os.path.join(raw_dir, filename)
        
        try:
            pages = extract_pages(pdf_path, doc_id)
            total_chars = sum(p["char_count"] for p in pages)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(pages, f, indent=2, ensure_ascii=False)
                
            print(f"Extracted {doc_id}: {len(pages)} pages, {total_chars} chars")
        except Exception as e:
            print(f"Failed to extract {doc_id}: {e}")
