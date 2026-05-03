# Codebase Graph — RAG Arena

Last updated: 2026-05-03 | Phase 3 ✅ COMPLETE | Phase 4 ✅ UI BUILT | Deployment 🔧 PENDING (Railway)

---

## Current State — What's Done

- **Phase 1:** Ingestion pipeline (downloader, extractor, chunker) — 1,367 chunks across 5 SEBI docs
- **Phase 2:** All 4 retrievers (Dense, BM25, Hybrid, Tree Index) + indexes built
- **Phase 3:** Generator + RAGAS 0.4 runner + full 41q × 4-strategy eval completed (run_12d94e65)
- **Phase 4:** FastAPI backend + HTML/JS frontend built. `Procfile`, `railway.json`, `nixpacks.toml` ready.
- **Pending:** Deploy to Railway — connect repo, set env vars (GROQ_API_KEY, GOOGLE_API_KEY, GENERATION_PROVIDER, GEMINI_MODEL), push.

---

## Eval Results Summary (run_12d94e65, 2026-05-03)

41 questions × 4 strategies = 163/164 rows (1 NaN: mh_02 × dense generation failure)

| Strategy   | Precision | Recall | Faithfulness | Ans. Relevance | Latency  | Tokens |
|------------|:---------:|:------:|:------------:|:--------------:|:--------:|:------:|
| BM25       | 0.036     | 0.274  | **0.932**    | 0.551          | **21ms** | 2702   |
| Dense      | 0.073     | 0.203  | 0.864        | 0.422          | 62ms     | 2299   |
| Hybrid     | 0.059     | **0.284** | 0.913     | **0.580**      | 822ms    | 2613   |
| Tree Index | **0.100** | 0.187  | 0.929        | 0.468          | 20,828ms | **674** |

Key findings: Hybrid = best general-purpose. BM25 = best when latency matters. Tree Index = keyword specialist only (0.375 precision on keyword, 0 on multihop/compound). See `findings.md` for full breakdown.

---

## Corpus State (ingested 2026-05-02)

| Document | Pages | Chunks | Status |
|----------|-------|--------|--------|
| sebi_lodr_2015 | 101 | 173 | ✅ Chunked |
| sebi_pit_2015 | 80 | 99 | ✅ Chunked |
| sebi_icdr_2018 | 471 | 700 | ✅ Chunked |
| sebi_sast_2011 | 79 | 104 | ✅ Chunked |
| sebi_mutual_fund_reg | 160 | 291 | ✅ Chunked |
| **Total** | **891** | **1,367** | |

RBI docs excluded — CDN geo-blocks programmatic download.

---

## Eval Dataset State (FINAL)

- `data/eval/questions.json` — **41 questions** (8 keyword, 11 semantic, 11 multihop, 11 compound). 11 removed: 10 required RBI corpus + kw_01 had truncated source regulation in corpus.
- `data/eval/ground_truth.json` — **41 hand-written ground truths**, verified against corpus chunks.
- `results/evals.db` — SQLite. Run `run_12d94e65` has 163 rows. Table: `eval_results`.

---

## RAGAS Pipeline — Key Implementation Notes

RAGAS 0.4.3 quirks (all fixed in `src/evaluation/ragas_runner.py`):
1. Import private classes: `_LLMContextPrecisionWithReference`, `_LLMContextRecall`, `_Faithfulness`, `_ResponseRelevancy` from `ragas.metrics`
2. Score key for precision: `"llm_context_precision_with_reference"` (not `"context_precision"`)
3. `RagasHFEmbeddings` lacks `embed_query` — use `_EmbeddingsWithQuery` wrapper subclass adding LangChain interface
4. `jsonref` must be installed explicitly (`uv pip install jsonref`) — undeclared dependency, silently returns NaN without it
5. Answer relevance suppressed by noncommittal multiplier — citation-style answers score 0. Relative comparisons valid, absolute values are not.

---

## API + Model Routing (actual, post-eval)

| Task | Model | Provider | Env var |
|------|-------|----------|---------|
| Tree Index leaf summarisation | gemini-2.0-flash (or GEMINI_MODEL) | Google | GOOGLE_API_KEY |
| Tree Index traversal | llama-3.3-70b-versatile | Groq | GROQ_API_KEY |
| Answer generation | llama-3.3-70b-versatile (or gemini) | Groq/Google | GENERATION_PROVIDER |
| RAGAS judge | same as generation | Groq/Google | GENERATION_PROVIDER |
| Embeddings | all-MiniLM-L6-v2 | Local | — |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Local | — |

Set `GENERATION_PROVIDER=gemini` to skip Groq for generation + RAGAS (use when Groq TPD exhausted).
Set `GEMINI_MODEL=gemini-2.0-flash` to avoid thinking token costs (Gemini 2.5 Flash costs ~10× more).

---

## File Registry

| File | Purpose | Exports | Status | Phase |
|------|---------|---------|--------|-------|
| rag-arena-spec.md | Project Specification | — | ✅ | 0 |
| CODEBASE_GRAPH.md | Agent Shared State | — | ✅ Current | 0 |
| findings.md | Eval results analysis + strategy guide | — | ✅ Complete | 3 |
| requirements.txt | All phase deps | — | ✅ | 1 |
| Makefile | Script shortcuts | — | ✅ | 1 |
| .pre-commit-config.yaml | black + ruff hooks | — | ✅ | 1 |
| .github/workflows/ci.yml | GitHub Actions CI | — | ✅ | 1 |
| data/corpus.json | PDF manifest | — | ✅ | 1 |
| src/ingestion/downloader.py | PDF Downloader | download_corpus | ✅ | 1 |
| src/ingestion/extractor.py | PDF Text Extractor | extract_pages, extract_corpus | ✅ | 1 |
| src/ingestion/chunker.py | Sentence-boundary chunker | chunk_document, save_chunks | ✅ | 1 |
| src/retrieval/base.py | Abstract base + TypedDicts | Chunk, RetrievalResult, BaseRetriever, timed_retrieve | ✅ | 1 |
| src/evaluation/logger.py | SQLite eval logger | init_db, log_row, fetch_all, fetch_run | ✅ | 1 |
| src/retrieval/dense.py | Dense FAISS Retriever | DenseRetriever | ✅ | 2 |
| src/retrieval/bm25.py | BM25 Retriever | BM25Retriever | ✅ | 2 |
| src/retrieval/hybrid.py | Hybrid Dense+BM25+CrossEncoder | HybridRetriever | ✅ | 2 |
| src/retrieval/tree_index.py | LlamaIndex Tree Index | TreeIndexRetriever | ✅ | 2 |
| src/generation/generator.py | LLM Answer Generator | generate, generate_from_env | ✅ | 3 |
| src/evaluation/ragas_runner.py | RAGAS 0.4.3 runner | run_ragas, run_ragas_from_env | ✅ | 3 |
| scripts/ingest.py | Ingestion pipeline CLI | — | ✅ | 1 |
| scripts/build_indexes.py | Index building CLI | — | ✅ | 2 |
| scripts/run_eval.py | Eval pipeline CLI | — | ✅ | 3 |
| data/eval/questions.json | 41 eval questions (final) | — | ✅ Final | 3 |
| data/eval/ground_truth.json | 41 hand-written ground truths | — | ✅ Final | 3 |
| data/eval/ground_truth_review.md | Review doc (reference only) | — | ✅ Done | 3 |
| docs/chunking_analysis.md | Chunking strategy analysis | — | ✅ | 3 |
| tests/fixtures/sample_pages.py | Synthetic test corpus | SAMPLE_PAGES | ✅ | 1 |
| tests/conftest.py | Load .env at pytest collection time | — | ✅ | 2 |
| tests/test_ingestion.py | Chunker unit tests (10 tests) | — | ✅ | 1 |
| tests/test_retrieval.py | Retrieval contract tests | — | ✅ | 1 |
| tests/test_retrieval_strategies.py | Phase 2 retriever unit tests | — | ✅ | 2 |
| tests/test_eval.py | Phase 3 eval pipeline unit tests | — | ✅ | 3 |
| notebooks/exploration.ipynb | Chunk quality inspection | — | ✅ | 1 |
| src/api/main.py | FastAPI backend (4 strategies, concurrent) | FastAPI app | ✅ | 4 |
| src/api/static/index.html | HTML/JS Chat Frontend | — | ✅ | 4 |
| src/api/__init__.py | API package init | — | ✅ | 4 |
| Procfile | Railway start command | — | ✅ | 4 |
| railway.json | Railway build/deploy config | — | ✅ | 4 |
| nixpacks.toml | Nixpacks — pre-downloads models at build | — | ✅ | 4 |
| scripts/preload_models.py | Pre-downloads embeddings + reranker | — | ✅ | 4 |
| results/evals.db | SQLite eval results (run_12d94e65) | — | ✅ | 3 |

---

## Interface Contracts — do not change without cascading updates

```
Chunk           = {id: str, text: str, doc_id: str, page: int, section: str}
RetrievalResult = {strategy: str, chunks: List[Chunk], latency_ms: float, token_cost: int}
EvalRow         = {query_id: str, strategy: str, context_precision: float, context_recall: float,
                   faithfulness: float, answer_relevance: float, latency_ms: float, token_cost: int}
```

RAGAS 0.4 returns `answer_relevancy`; ragas_runner.py maps it to `answer_relevance`.

---

## Dependency Map

```
data/corpus.json → downloader → data/raw/*.pdf → extractor → data/processed/*.json
    → chunker → data/chunks/*_chunks.json → build_indexes → data/indexes/*

data/indexes/* + data/eval/questions.json + data/eval/ground_truth.json
    → scripts/run_eval.py → results/evals.db
        (retrieve → generate_from_env → run_ragas_from_env → log_row)

data/indexes/* → src/api/main.py (FastAPI, concurrent.futures) → src/api/static/index.html
results/evals.db → GET /results → frontend charts tab
```

---

## Review Status

| File | Verdict | Security | Notes |
|------|---------|----------|-------|
| src/ingestion/downloader.py | ✅ | ✅ | — |
| src/ingestion/extractor.py | ✅ | ✅ | — |
| src/ingestion/chunker.py | ✅ | ✅ | Known weakness: footnote noise in ICDR |
| src/retrieval/base.py | ✅ | ✅ | — |
| src/retrieval/dense.py | ✅ | ✅ | L2-normalize + IndexFlatIP |
| src/retrieval/bm25.py | ✅ | ✅ | — |
| src/retrieval/hybrid.py | ✅ | ✅ | Dedup by chunk id |
| src/retrieval/tree_index.py | ✅ | ✅ | GEMINI_MODEL env var respected; Groq primary |
| src/evaluation/logger.py | ✅ | ✅ | All SQL parameterized |
| src/generation/generator.py | ✅ | ✅ | — |
| src/evaluation/ragas_runner.py | ✅ | ✅ | RAGAS 0.4.3 quirks documented above |
| scripts/run_eval.py | ✅ | ✅ | Cost guard mandatory |
| src/api/main.py | ✅ | ✅ | Concurrent strategies; graceful tree_index skip |
| src/api/static/index.html | ✅ | ✅ | — |
| tests/ | ✅ | ✅ | 33 passed |
