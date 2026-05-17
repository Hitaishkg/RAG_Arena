import os
from sentence_transformers import CrossEncoder
from src.retrieval.base import BaseRetriever, Chunk, RetrievalResult
from src.retrieval.dense import DenseRetriever
from src.retrieval.bm25 import BM25Retriever

class HybridRetriever(BaseRetriever):
    """Hybrid retriever that fuses Dense + BM25 results using a cross-encoder reranker."""

    def __init__(
        self,
        chunks: list[Chunk],
        dense_model: str = "BAAI/bge-small-en-v1.5",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        candidate_k: int = 10,
    ):
        super().__init__(chunks)
        self.dense_model = dense_model
        self.reranker_model = reranker_model
        self.candidate_k = candidate_k
        self._dense: DenseRetriever = None
        self._bm25: BM25Retriever = None
        self._reranker = None

    def build_index(self) -> None:
        """Build Dense and BM25 sub-retrievers and load reranker."""
        self._dense = DenseRetriever(self.chunks, self.dense_model)
        self._dense.build_index()

        self._bm25 = BM25Retriever(self.chunks)
        self._bm25.build_index()

        from sentence_transformers import CrossEncoder
        self._reranker = CrossEncoder(self.reranker_model)

    def retrieve(self, query: str, k: int = 5) -> RetrievalResult:
        """Retrieve top-k chunks using dense + bm25 candidates and cross-encoder reranking."""
        if not self._dense or not self._bm25 or not self._reranker:
            raise RuntimeError("Index not built or loaded. Call build_index() or load_index() first.")

        # Get top-candidate_k from Dense
        dense_result = self._dense.retrieve(query, self.candidate_k)
        
        # Get top-candidate_k from BM25
        bm25_result = self._bm25.retrieve(query, self.candidate_k)

        # Deduplicate by chunk id
        seen_ids = set()
        candidates = []
        for chunk in dense_result["chunks"] + bm25_result["chunks"]:
            if chunk["id"] not in seen_ids:
                seen_ids.add(chunk["id"])
                candidates.append(chunk)

        # Rerank candidates with cross-encoder
        if not candidates:
            return RetrievalResult(strategy="hybrid", chunks=[], latency_ms=0.0, token_cost=0)

        pairs = [[query, c["text"]] for c in candidates]
        scores = self._reranker.predict(pairs)
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        top_chunks = [c for _, c in ranked[:k]]

        return RetrievalResult(strategy="hybrid", chunks=top_chunks, latency_ms=0.0, token_cost=0)

    def save_index(self, path: str) -> None:
        """Save Dense and BM25 indexes."""
        if not self._dense or not self._bm25:
            raise RuntimeError("Sub-retrievers not initialized.")
            
        self._dense.save_index(path + ".dense")
        self._bm25.save_index(path + ".bm25")

    def load_index(self, path: str) -> None:
        """Load Dense and BM25 indexes and initialize reranker."""
        self._dense = DenseRetriever(self.chunks, self.dense_model)
        self._dense.load_index(path + ".dense")
        
        self._bm25 = BM25Retriever(self.chunks)
        self._bm25.load_index(path + ".bm25")
        
        from sentence_transformers import CrossEncoder
        self._reranker = CrossEncoder(self.reranker_model)
