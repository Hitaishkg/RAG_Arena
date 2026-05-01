import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
import json
import glob
from dotenv import load_dotenv

load_dotenv()

from src.retrieval.dense import DenseRetriever
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.tree_index import TreeIndexRetriever


def load_all_chunks(chunks_dir: str) -> list:
    all_chunks = []
    for path in sorted(glob.glob(os.path.join(chunks_dir, "*_chunks.json"))):
        with open(path) as f:
            all_chunks.extend(json.load(f))
    return all_chunks


def main():
    parser = argparse.ArgumentParser(description="Build retrieval indexes for all strategies")
    parser.add_argument(
        "--chunks-dir", default="data/chunks", help="Directory with *_chunks.json files"
    )
    parser.add_argument("--index-dir", default="data/indexes", help="Directory to save indexes")
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["dense", "bm25", "hybrid", "tree_index"],
        choices=["dense", "bm25", "hybrid", "tree_index"],
        help="Which strategies to build",
    )
    args = parser.parse_args()

    os.makedirs(args.index_dir, exist_ok=True)

    print(f"Loading chunks from {args.chunks_dir}...")
    chunks = load_all_chunks(args.chunks_dir)
    if not chunks:
        print("No chunks found. Run scripts/ingest.py first.")
        sys.exit(1)
    print(f"Loaded {len(chunks)} chunks.")

    if "dense" in args.strategies:
        print("\nBuilding Dense index...")
        retriever = DenseRetriever(chunks)
        retriever.build_index()
        retriever.save_index(os.path.join(args.index_dir, "dense.index"))
        print("Dense index saved.")

    if "bm25" in args.strategies:
        print("\nBuilding BM25 index...")
        retriever = BM25Retriever(chunks)
        retriever.build_index()
        retriever.save_index(os.path.join(args.index_dir, "bm25.index"))
        print("BM25 index saved.")

    if "hybrid" in args.strategies:
        print("\nBuilding Hybrid index (Dense + BM25 + CrossEncoder)...")
        retriever = HybridRetriever(chunks)
        retriever.build_index()
        retriever.save_index(os.path.join(args.index_dir, "hybrid.index"))
        print("Hybrid index saved.")

    if "tree_index" in args.strategies:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("\nSkipping Tree Index: GOOGLE_API_KEY not set.")
        else:
            print("\nBuilding Tree Index (LlamaIndex + Gemini 1.5 Flash)...")
            retriever = TreeIndexRetriever(chunks, api_key=api_key)
            retriever.build_index()
            retriever.save_index(os.path.join(args.index_dir, "tree_index"))
            print("Tree Index saved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
