from abc import ABC, abstractmethod
from typing import TypedDict
import time

class Chunk(TypedDict):
    id: str
    text: str
    doc_id: str
    page: int
    section: str

class RetrievalResult(TypedDict):
    strategy: str
    chunks: list[Chunk]
    latency_ms: float
    token_cost: int

class BaseRetriever(ABC):
    """Abstract base for all retrieval strategies."""

    def __init__(self, chunks: list[Chunk]):
        """
        Initialise with a list of Chunk dicts (already loaded from disk).
        Subclasses call super().__init__(chunks) then do their own index build.
        """
        self.chunks = chunks

    @abstractmethod
    def build_index(self) -> None:
        """Build or load the retrieval index from self.chunks."""

    @abstractmethod
    def retrieve(self, query: str, k: int = 5) -> RetrievalResult:
        """
        Retrieve top-k chunks for query.
        Must return a RetrievalResult with:
          - strategy: strategy name string
          - chunks: list of Chunk dicts (up to k items)
          - latency_ms: wall-clock time for the retrieve call (float, ms)
          - token_cost: number of tokens consumed (0 for non-LLM strategies)
        """

    @abstractmethod
    def save_index(self, path: str) -> None:
        """Serialise the built index to disk at given path."""

    @abstractmethod
    def load_index(self, path: str) -> None:
        """Load a previously serialised index from disk."""

def timed_retrieve(retriever: BaseRetriever, query: str, k: int = 5) -> RetrievalResult:
    """
    Call retriever.retrieve(query, k) and ensure latency_ms is set.
    If the retriever sets it, use that value. Otherwise measure wall-clock.
    """
    start = time.perf_counter()
    result = retriever.retrieve(query, k)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if result["latency_ms"] == 0.0:
        result["latency_ms"] = round(elapsed_ms, 2)
    return result
