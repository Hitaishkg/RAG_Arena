# Codebase Graph — RAG Arena

Last updated: 2026-05-01 | Phase: 2 - Retrieval Pipelines ✅ COMPLETE

## File Registry

| File | Purpose | Exports | Status | Phase |
|------|---------|---------|--------|-------|
| rag-arena-spec.md | Project Specification | - | ✅ Reviewed | 0 |
| GEMINI.md | Agent Instructions | - | ✅ Reviewed | 0 |
| CODEBASE_GRAPH.md | Agent Shared State | - | ✅ Reviewed | 0 |
| requirements.txt | Phase 1+2 dependencies | - | ✅ Reviewed | 1 |
| Makefile | Script shortcuts | - | ✅ Reviewed | 1 |
| .pre-commit-config.yaml | black + ruff hooks | - | ✅ Reviewed | 1 |
| .github/workflows/ci.yml | GitHub Actions CI | - | ✅ Reviewed | 1 |
| data/corpus.json | PDF download manifest | - | ✅ Reviewed | 1 |
| src/ingestion/downloader.py | PDF Downloader | download_corpus | ✅ Reviewed | 1 |
| src/ingestion/extractor.py | PDF Text Extractor | extract_pages, extract_corpus | ✅ Reviewed | 1 |
| src/ingestion/chunker.py | Sentence-boundary chunker (bug fix applied) | detect_section, chunk_text, chunk_document, save_chunks | ✅ Reviewed | 1 |
| src/retrieval/base.py | Abstract base + TypedDicts | Chunk, RetrievalResult, BaseRetriever, timed_retrieve | ✅ Reviewed | 1 |
| src/evaluation/logger.py | SQLite eval logger | init_db, log_row, fetch_all, fetch_run | ✅ Reviewed | 1 |
| src/retrieval/dense.py | Dense FAISS Retriever | DenseRetriever | ✅ Reviewed | 2 |
| src/retrieval/bm25.py | BM25 rank-bm25 Retriever | BM25Retriever | ✅ Reviewed | 2 |
| src/retrieval/hybrid.py | Hybrid Dense+BM25 Retriever | HybridRetriever | ✅ Reviewed | 2 |
| src/retrieval/tree_index.py | LlamaIndex Tree Index Retriever | TreeIndexRetriever | ✅ Reviewed | 2 |
| scripts/ingest.py | Ingestion pipeline CLI | - | ✅ Reviewed | 1 |
| scripts/build_indexes.py | Index building CLI | - | ✅ Reviewed | 2 |
| tests/fixtures/sample_pages.py | Synthetic test corpus | SAMPLE_PAGES | ✅ Reviewed | 1 |
| tests/test_ingestion.py | Chunker unit tests (10 tests) | - | ✅ Reviewed | 1 |
| tests/test_retrieval.py | Retrieval contract tests | - | ✅ Reviewed | 1 |
| tests/test_retrieval_strategies.py | Unit tests for Phase 2 retrievers | - | ✅ Reviewed | 2 |
| notebooks/exploration.ipynb | Chunk quality inspection notebook | - | ✅ Reviewed | 1 |

## Interface Contracts

Shared data types that all modules must respect. Do not change these without updating all dependent files.

### Chunk
{id: str, text: str, doc_id: str, page: int, section: str}

### RetrievalResult
{strategy: str, chunks: List[Chunk], latency_ms: float, token_cost: int}

### EvalRow
{query_id: str, strategy: str, context_precision: float, context_recall: float,
 faithfulness: float, answer_relevance: float, latency_ms: float, token_cost: int}

## Dependency Map

```
data/corpus.json → downloader.py → data/raw/<doc_id>.pdf
                                 → extractor.py → data/processed/<doc_id>.json
                                               → chunker.py → data/chunks/<doc_id>_chunks.json
                                                            → retrieval/* (all 4 strategies read chunks)
src/retrieval/base.py → dense.py, bm25.py, hybrid.py, tree_index.py
hybrid.py → dense.py + bm25.py + CrossEncoder reranker
data/chunks/*_chunks.json → scripts/build_indexes.py → data/indexes/*
src/evaluation/logger.py → Phase 3 eval loop
scripts/ingest.py → orchestrates downloader + extractor + chunker
```

## Review Status

| File | Reviewer verdict | Security verdict | Notes |
|------|-----------------|-----------------|-------|
| rag-arena-spec.md | ✅ Approved | ✅ Clean | Source of truth |
| src/ingestion/downloader.py | ✅ Approved | ✅ Clean | — |
| src/ingestion/extractor.py | ✅ Approved | ✅ Clean | — |
| src/ingestion/chunker.py | ✅ Approved | ✅ Clean | Infinite-loop bug fixed by Claude (overlap + long sentence edge case) |
| src/retrieval/base.py | ✅ Approved | ✅ Clean | — |
| src/evaluation/logger.py | ✅ Approved | ✅ Clean | All SQL parameterized |
| scripts/ingest.py | ✅ Approved | ✅ Clean | doc_id from own files only |
| src/retrieval/dense.py | ✅ Approved | ✅ Clean | O(n) scan replaced with O(1) direct index; float32 + L2-normalize verified |
| src/retrieval/bm25.py | ✅ Approved | ✅ Clean | pickle is local-disk-only, no untrusted input |
| src/retrieval/hybrid.py | ✅ Approved | ✅ Clean | dedup by chunk id; CrossEncoder local model |
| src/retrieval/tree_index.py | ✅ Approved | ✅ Clean | LlamaIndex imports lazy (inside methods); api_key from env |
| scripts/build_indexes.py | ✅ Approved | ✅ Clean | GOOGLE_API_KEY gated; exits cleanly if no chunks |
| tests/ | ✅ Approved | ✅ Clean | 26 passed, 2 skipped (Tree Index — no GOOGLE_API_KEY in CI) |
