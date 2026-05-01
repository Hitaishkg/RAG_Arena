import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.ingestion.chunker import chunk_document
from tests.fixtures.sample_pages import SAMPLE_PAGES

@pytest.fixture(scope="module")
def test_chunks():
    return chunk_document(SAMPLE_PAGES)

# Dense retriever tests (3 tests)

def test_dense_build_and_retrieve(test_chunks):
    from src.retrieval.dense import DenseRetriever
    r = DenseRetriever(test_chunks)
    r.build_index()
    result = r.retrieve("disclosure requirements", k=3)
    assert result["strategy"] == "dense"
    assert len(result["chunks"]) <= 3
    assert result["token_cost"] == 0
    assert all(isinstance(c["id"], str) for c in result["chunks"])

def test_dense_result_fields(test_chunks):
    from src.retrieval.dense import DenseRetriever
    r = DenseRetriever(test_chunks)
    r.build_index()
    result = r.retrieve("insider trading", k=2)
    assert "strategy" in result and "chunks" in result
    assert "latency_ms" in result and "token_cost" in result
    for chunk in result["chunks"]:
        assert set(chunk.keys()) == {"id", "text", "doc_id", "page", "section"}

def test_dense_save_load(test_chunks, tmp_path):
    from src.retrieval.dense import DenseRetriever
    index_path = str(tmp_path / "dense.index")
    r1 = DenseRetriever(test_chunks)
    r1.build_index()
    r1.save_index(index_path)
    r2 = DenseRetriever(test_chunks)
    r2.load_index(index_path)
    result = r2.retrieve("penalties", k=2)
    assert len(result["chunks"]) <= 2
    assert result["strategy"] == "dense"

# BM25 retriever tests (3 tests)

def test_bm25_build_and_retrieve(test_chunks):
    from src.retrieval.bm25 import BM25Retriever
    r = BM25Retriever(test_chunks)
    r.build_index()
    result = r.retrieve("compliance officer", k=3)
    assert result["strategy"] == "bm25"
    assert len(result["chunks"]) <= 3
    assert result["token_cost"] == 0

def test_bm25_result_fields(test_chunks):
    from src.retrieval.bm25 import BM25Retriever
    r = BM25Retriever(test_chunks)
    r.build_index()
    result = r.retrieve("regulations", k=2)
    for chunk in result["chunks"]:
        assert set(chunk.keys()) == {"id", "text", "doc_id", "page", "section"}

def test_bm25_save_load(test_chunks, tmp_path):
    from src.retrieval.bm25 import BM25Retriever
    index_path = str(tmp_path / "bm25.index")
    r1 = BM25Retriever(test_chunks)
    r1.build_index()
    r1.save_index(index_path)
    r2 = BM25Retriever(test_chunks)
    r2.load_index(index_path)
    result = r2.retrieve("definition", k=2)
    assert result["strategy"] == "bm25"

# Hybrid retriever tests (2 tests)

def test_hybrid_build_and_retrieve(test_chunks):
    from src.retrieval.hybrid import HybridRetriever
    r = HybridRetriever(test_chunks, candidate_k=5)
    r.build_index()
    result = r.retrieve("listed entity obligations", k=3)
    assert result["strategy"] == "hybrid"
    assert len(result["chunks"]) <= 3
    assert result["token_cost"] == 0
    for chunk in result["chunks"]:
        assert set(chunk.keys()) == {"id", "text", "doc_id", "page", "section"}

def test_hybrid_deduplication(test_chunks):
    from src.retrieval.hybrid import HybridRetriever
    r = HybridRetriever(test_chunks, candidate_k=5)
    r.build_index()
    result = r.retrieve("insider trading penalties", k=5)
    ids = [c["id"] for c in result["chunks"]]
    assert len(ids) == len(set(ids))

# Tree Index tests (2 tests — SKIP if no GOOGLE_API_KEY)

@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set — skipping Tree Index tests"
)
@pytest.mark.flaky(reruns=3, reruns_delay=20)
def test_tree_index_build_and_retrieve(test_chunks):
    from src.retrieval.tree_index import TreeIndexRetriever
    r = TreeIndexRetriever(test_chunks)
    r.build_index()
    result = r.retrieve("what are the disclosure obligations for listed entities?", k=3)
    assert result["strategy"] == "tree_index"
    assert len(result["chunks"]) <= 3
    assert isinstance(result["token_cost"], int)

@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set — skipping Tree Index tests"
)
@pytest.mark.flaky(reruns=3, reruns_delay=20)
def test_tree_index_save_load(test_chunks, tmp_path):
    from src.retrieval.tree_index import TreeIndexRetriever
    index_path = str(tmp_path / "tree_index")
    r1 = TreeIndexRetriever(test_chunks)
    r1.build_index()
    r1.save_index(index_path)
    r2 = TreeIndexRetriever(test_chunks)
    r2.load_index(index_path)
    result = r2.retrieve("compliance officer duties", k=2)
    assert result["strategy"] == "tree_index"
