import os
import pickle
from rank_bm25 import BM25Okapi
from src.retrieval.base import BaseRetriever, Chunk, RetrievalResult

class BM25Retriever(BaseRetriever):
    def __init__(self, chunks: list[Chunk]):
        super().__init__(chunks)
        self.bm25 = None
        self._tokenized_corpus: list[list[str]] = []

    def build_index(self) -> None:
        """Tokenize each chunk: lowercase + split on whitespace and build BM25 index."""
        self._tokenized_corpus = [c["text"].lower().split() for c in self.chunks]
        self.bm25 = BM25Okapi(self._tokenized_corpus)

    def retrieve(self, query: str, k: int = 5) -> RetrievalResult:
        """Tokenize query and retrieve top-k chunks using BM25."""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_k_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        retrieved_chunks = [self.chunks[i] for i in top_k_indices]
        
        return RetrievalResult(
            strategy="bm25",
            chunks=retrieved_chunks,
            latency_ms=0.0,
            token_cost=0
        )

    def save_index(self, path: str) -> None:
        """Serialize using pickle."""
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
            
        with open(path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "tokenized_corpus": self._tokenized_corpus}, f)

    def load_index(self, path: str) -> None:
        """Load pickle: restore self.bm25 and self._tokenized_corpus."""
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.bm25 = data["bm25"]
            self._tokenized_corpus = data["tokenized_corpus"]
