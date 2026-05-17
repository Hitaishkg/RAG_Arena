import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from src.retrieval.base import BaseRetriever, Chunk, RetrievalResult

class DenseRetriever(BaseRetriever):
    """Dense retriever using sentence-transformers and FAISS IndexFlatIP."""

    # BGE models need this prefix on queries (not on documents) for retrieval tasks
    _BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

    def __init__(self, chunks: list[Chunk], model_name: str = "BAAI/bge-small-en-v1.5"):
        super().__init__(chunks)
        self.model_name = model_name
        self.model = None
        self.index = None
        self._chunk_ids: list[str] = []

    def build_index(self) -> None:
        """Build FAISS index from chunks using L2-normalized embeddings."""
        self.model = SentenceTransformer(self.model_name)
        
        # Encode all chunk texts
        embeddings = self.model.encode(
            [c["text"] for c in self.chunks], 
            show_progress_bar=False, 
            convert_to_numpy=True
        ).astype("float32")
        
        # L2-normalize all embeddings for IndexFlatIP (cosine similarity)
        faiss.normalize_L2(embeddings)
        
        # Create FAISS Index
        d = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(d)
        self.index.add(embeddings)
        
        # Store chunk IDs for mapping search results
        self._chunk_ids = [c["id"] for c in self.chunks]

    def retrieve(self, query: str, k: int = 5) -> RetrievalResult:
        """Retrieve top-k chunks using inner product on normalized embeddings."""
        if not self.index or not self.model:
            raise RuntimeError("Index not built. Call build_index() or load_index() first.")

        # Encode query (BGE models use an instruction prefix for retrieval)
        q_text = self._BGE_QUERY_PREFIX + query if "bge" in self.model_name.lower() else query
        q_emb = self.model.encode([q_text], convert_to_numpy=True).astype("float32")
        
        # L2-normalize query
        faiss.normalize_L2(q_emb)
        
        # Search
        scores, indices = self.index.search(q_emb, k)
        
        # Map indices to chunks (skip any index == -1)
        retrieved_chunks = []
        for idx in indices[0]:
            if idx == -1:
                continue
            retrieved_chunks.append(self.chunks[idx])

        return RetrievalResult(
            strategy="dense",
            chunks=retrieved_chunks,
            latency_ms=0.0,
            token_cost=0
        )

    def save_index(self, path: str) -> None:
        """Save FAISS index and metadata to disk."""
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
            
        faiss.write_index(self.index, path)
        
        meta = {
            "chunk_ids": self._chunk_ids,
            "model_name": self.model_name
        }
        with open(path + ".meta.json", "w") as f:
            json.dump(meta, f)

    def load_index(self, path: str) -> None:
        """Load FAISS index and metadata from disk."""
        self.index = faiss.read_index(path)
        
        with open(path + ".meta.json", "r") as f:
            meta = json.load(f)
            
        self._chunk_ids = meta["chunk_ids"]
        self.model_name = meta["model_name"]
        
        # Load the model
        self.model = SentenceTransformer(self.model_name)
