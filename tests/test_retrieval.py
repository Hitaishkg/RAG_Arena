import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.retrieval.base import Chunk, RetrievalResult, BaseRetriever

def test_chunk_typeddict_fields():
    """Chunk TypedDict has expected keys."""
    # Note: TypedDict does not enforce keys at runtime, but we can check if a dict matches the keys
    chunk: Chunk = {"id": "x", "text": "t", "doc_id": "d", "page": 1, "section": "S"}
    assert set(chunk.keys()) == {"id", "text", "doc_id", "page", "section"}

def test_retrieval_result_typeddict_fields():
    """RetrievalResult TypedDict has expected keys."""
    result: RetrievalResult = {"strategy": "dense", "chunks": [], "latency_ms": 0.0, "token_cost": 0}
    assert set(result.keys()) == {"strategy", "chunks", "latency_ms", "token_cost"}

def test_base_retriever_is_abstract():
    """BaseRetriever cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseRetriever([])  # type: ignore

# Placeholder — will be filled in Phase 2
@pytest.mark.skip(reason="Dense retriever not implemented until Phase 2")
def test_dense_retriever_returns_result():
    pass

@pytest.mark.skip(reason="BM25 retriever not implemented until Phase 2")
def test_bm25_retriever_returns_result():
    pass
