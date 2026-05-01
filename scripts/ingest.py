import sys
import os

# sys.path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
import json
from dotenv import load_dotenv
from src.ingestion.downloader import download_corpus
from src.ingestion.extractor import extract_corpus
from src.ingestion.chunker import chunk_document, save_chunks

# Load .env right after imports
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="End-to-end ingestion pipeline CLI")
    
    # Defaults from env vars with fallbacks
    data_dir = os.getenv("DATA_DIR", "data/")
    chunk_size_default = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap_default = int(os.getenv("CHUNK_OVERLAP", "64"))

    parser.add_argument("--corpus", default="data/corpus.json", help="Path to corpus manifest")
    parser.add_argument("--raw-dir", default=os.path.join(data_dir, "raw"), help="Directory for raw PDFs")
    parser.add_argument("--processed-dir", default=os.path.join(data_dir, "processed"), help="Directory for extracted JSONs")
    parser.add_argument("--chunks-dir", default=os.path.join(data_dir, "chunks"), help="Directory for saved chunks")
    parser.add_argument("--chunk-size", type=int, default=chunk_size_default, help="Chunk size in tokens")
    parser.add_argument("--overlap", type=int, default=chunk_overlap_default, help="Chunk overlap in tokens")
    parser.add_argument("--skip-download", action="store_true", help="Skip download step")
    parser.add_argument("--skip-extract", action="store_true", help="Skip extraction step")

    args = parser.parse_args()

    # Step 1 — Download
    if not args.skip_download:
        print(f"Step 1: Downloading corpus from {args.corpus} to {args.raw_dir}...")
        results = download_corpus(args.corpus, args.raw_dir)
        ok_count = sum(1 for r in results if r["status"] == "ok")
        failed_count = sum(1 for r in results if r["status"].startswith("failed"))
        print(f"Downloaded: {ok_count} ok, {failed_count} failed")
    else:
        print("Step 1: Skipping download.")

    # Step 2 — Extract
    if not args.skip_extract:
        print(f"Step 2: Extracting PDFs from {args.raw_dir} to {args.processed_dir}...")
        extract_corpus(args.raw_dir, args.processed_dir)
    else:
        print("Step 2: Skipping extraction.")

    # Step 3 — Chunk
    print(f"Step 3: Chunking documents from {args.processed_dir} to {args.chunks_dir}...")
    os.makedirs(args.chunks_dir, exist_ok=True)
    
    total_chunks = 0
    total_docs = 0
    
    if os.path.exists(args.processed_dir):
        # Sort files to ensure consistent order
        filenames = sorted([f for f in os.listdir(args.processed_dir) if f.endswith(".json")])
        for filename in filenames:
            doc_id = filename[:-5]
            input_path = os.path.join(args.processed_dir, filename)
            
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    pages = json.load(f)
                
                chunks = chunk_document(pages, args.chunk_size, args.overlap)
                save_chunks(chunks, os.path.join(args.chunks_dir, f"{doc_id}_chunks.json"))
                
                print(f"Chunked {doc_id}: {len(chunks)} chunks")
                total_chunks += len(chunks)
                total_docs += 1
            except Exception as e:
                print(f"Failed to chunk {doc_id}: {e}")
    
    print(f"Total: {total_chunks} chunks across {total_docs} documents")
    print("Ingestion complete.")

if __name__ == "__main__":
    main()
