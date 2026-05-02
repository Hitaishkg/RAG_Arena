"""Pre-download sentence-transformers models during Railway build phase.
Run once at build time so cold starts don't re-download from HuggingFace.
"""
import sys

print("Pre-downloading embedding model...")
from sentence_transformers import SentenceTransformer
SentenceTransformer("all-MiniLM-L6-v2")
print("  all-MiniLM-L6-v2 cached.")

print("Pre-downloading cross-encoder model...")
from sentence_transformers import CrossEncoder
CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
print("  cross-encoder/ms-marco-MiniLM-L-6-v2 cached.")

print("Models ready.")
sys.exit(0)
