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

def test_dense_retriever_returns_result():
    from src.retrieval.dense import DenseRetriever
    chunks = [
        {"id": "1", "text": "The quick brown fox", "doc_id": "A", "page": 1, "section": "Intro"},
        {"id": "2", "text": "jumped over the lazy dog", "doc_id": "A", "page": 1, "section": "Intro"},
    ]
    retriever = DenseRetriever(chunks)
    retriever.build_index()
    result = retriever.retrieve("fox")
    
    assert result["strategy"] == "dense"
    assert len(result["chunks"]) > 0
    assert result["latency_ms"] == 0.0
    assert result["token_cost"] == 0

def test_hybrid_retriever_returns_result():
    from src.retrieval.hybrid import HybridRetriever
    chunks = [
        {"id": "1", "text": "The quick brown fox", "doc_id": "A", "page": 1, "section": "Intro"},
        {"id": "2", "text": "jumped over the lazy dog", "doc_id": "A", "page": 1, "section": "Intro"},
        {"id": "3", "text": "The weather is nice today", "doc_id": "B", "page": 1, "section": "Misc"},
    ]
    retriever = HybridRetriever(chunks)
    retriever.build_index()
    result = retriever.retrieve("What did the fox do?", k=2)
    
    assert result["strategy"] == "hybrid"
    assert len(result["chunks"]) <= 2
    assert result["latency_ms"] == 0.0
    assert result["token_cost"] == 0

def test_hybrid_retriever_save_load(tmp_path):
    from src.retrieval.hybrid import HybridRetriever
    chunks = [{"id": "1", "text": "test chunk", "doc_id": "A", "page": 1, "section": "S"}]
    retriever = HybridRetriever(chunks)
    retriever.build_index()
    
    index_base_path = str(tmp_path / "hybrid_index")
    retriever.save_index(index_base_path)
    
    # Check if sub-index files exist
    assert os.path.exists(index_base_path + ".dense")
    assert os.path.exists(index_base_path + ".dense.meta.json")
    assert os.path.exists(index_base_path + ".bm25")
    
    new_retriever = HybridRetriever(chunks)
    new_retriever.load_index(index_base_path)
    
    assert new_retriever._dense is not None
    assert new_retriever._bm25 is not None
    assert new_retriever._reranker is not None
    
    result = new_retriever.retrieve("test")
    assert result["chunks"][0]["text"] == "test chunk"

def test_bm25_retriever_returns_result():
    from src.retrieval.bm25 import BM25Retriever
    chunks = [
        {"id": "1", "text": "The quick brown fox", "doc_id": "A", "page": 1, "section": "Intro"},
        {"id": "2", "text": "jumped over the lazy dog", "doc_id": "A", "page": 1, "section": "Intro"},
    ]
    retriever = BM25Retriever(chunks)
    retriever.build_index()
    result = retriever.retrieve("fox")
    
    assert result["strategy"] == "bm25"
    assert len(result["chunks"]) > 0
    assert result["chunks"][0]["text"] == "The quick brown fox"
    assert result["latency_ms"] == 0.0
    assert result["token_cost"] == 0

def test_bm25_retriever_save_load(tmp_path):
    from src.retrieval.bm25 import BM25Retriever
    chunks = [{"id": "1", "text": "test chunk", "doc_id": "A", "page": 1, "section": "S"}]
    retriever = BM25Retriever(chunks)
    retriever.build_index()
    
    index_path = str(tmp_path / "bm25.pkl")
    retriever.save_index(index_path)
    
    new_retriever = BM25Retriever(chunks)
    new_retriever.load_index(index_path)
    
    assert new_retriever.bm25 is not None
    assert new_retriever._tokenized_corpus == [["test", "chunk"]]
    
    result = new_retriever.retrieve("test")
    assert result["chunks"][0]["text"] == "test chunk"
