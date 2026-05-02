# Codebase Graph — RAG Arena

Last updated: 2026-05-02 | Phase: 3 ✅ COMPLETE | Phase: 4 - Chat UI + Deployment 🔧 IN PROGRESS

---

## Phase 4 Plan (NEXT)
**Goal:** FastAPI backend + HTML/JS frontend. Live chat interface where user types a question and sees all 4 strategy answers side-by-side. Deploy to Railway/Render.

**Architecture:**
```
POST /query {question, k=5}
→ run all 4 strategies in parallel (concurrent.futures)
→ return {dense, bm25, hybrid, tree_index}: {answer, chunks, latency_ms, token_cost}

GET /health → liveness probe
GET /results → aggregate eval results from evals.db
```

**Frontend:** Single HTML page + vanilla JS. No React. 4 columns, each showing answer + latency + expandable chunks. Second tab: aggregate charts from evals.db.

**Deployment:** Railway (free tier, 512MB RAM sufficient for FAISS + BM25 + indexes). Indexes pre-built locally, committed to git (estimated <20MB total).

---

## Corpus State (ingested 2026-05-02)

| Document | Pages | Chunks | Status |
|----------|-------|--------|--------|
| sebi_lodr_2015 | 101 | 173 | ✅ Chunked |
| sebi_pit_2015 | 80 | 99 | ✅ Chunked |
| sebi_icdr_2018 | 471 | 700 | ✅ Chunked |
| sebi_sast_2011 | 79 | 104 | ✅ Chunked |
| sebi_mutual_fund_reg | 160 | 291 | ✅ Chunked |
| rbi_kyc_master_dir | — | — | ❌ CDN geo-blocks programmatic download |
| rbi_nbfc_master_dir | — | — | ❌ CDN geo-blocks programmatic download |
| **Total** | **891** | **1,367** | |

RBI impact: 8 eval questions (kw_05, kw_08, sem_07, sem_12, mh_01, mh_06, cp_03, cp_07) will have no ground truth; they score on 3/4 RAGAS metrics.

---

## Eval Dataset State

- `data/eval/questions.json` — 50 questions (13 keyword, 13 semantic, 13 multihop, 11 compound)
- `data/eval/ground_truth_review.md` — **NEEDS USER REVIEW** — ground truths extracted from 5 SEBI PDFs, source + page cited. Top section lists 10 questions to replace (RBI questions + 2 unanswerable from corpus).
- `data/eval/ground_truth.json` — stubs; to be populated after user review of ground_truth_review.md
- **Blockers before running eval:** (1) user reviews ground_truth_review.md; (2) build_indexes.py has not been run yet

---

## Chunking Strategy (see docs/chunking_analysis.md for full analysis)

- Sentence-boundary, 512-token budget, 64-token overlap, per-page granularity
- NLTK sent_tokenize — never cuts mid-sentence (critical for legal text)
- **Known weaknesses:** (1) amendment footnotes contaminate ~30-40% of ICDR chunks; (2) no cross-page overlap (cross-page regulations split into isolated chunks); (3) section detection matches very few SEBI headings
- **Eval hypothesis:** Tree Index should outperform on multihop/compound questions precisely because it summarises across chunks, compensating for weakness (2)

---

## API + Model Routing (locked)

| Task | Model | Provider | Limit |
|------|-------|----------|-------|
| Tree Index leaf summarisation | llama-3.1-8b-instant | Groq | 14,400 req/day |
| Tree Index traversal | llama-3.3-70b-versatile | Groq | 1,000 req/day |
| Answer generation | llama-3.3-70b-versatile | Groq | 1,000 req/day |
| RAGAS judge | llama-3.3-70b-versatile | Groq | 1,000 req/day |
| Embeddings | all-MiniLM-L6-v2 | Local | — |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Local | — |

Gemini 2.5-flash (GOOGLE_API_KEY) is fallback only. Both keys in `.env` (gitignored).
Full eval run: ~200 generation calls + ~800 RAGAS calls on 70B → may need 2 days within 1,000 req/day limit. Use `--strategies` flag to run one strategy per day.

---

## File Registry

| File | Purpose | Exports | Status | Phase |
|------|---------|---------|--------|-------|
| rag-arena-spec.md | Project Specification | — | ✅ Reviewed | 0 |
| CODEBASE_GRAPH.md | Agent Shared State | — | ✅ Current | 0 |
| requirements.txt | All phase deps (ragas>=0.4, langchain-*, instructor) | — | ✅ Reviewed | 1 |
| Makefile | Script shortcuts | — | ✅ Reviewed | 1 |
| .pre-commit-config.yaml | black + ruff hooks | — | ✅ Reviewed | 1 |
| .github/workflows/ci.yml | GitHub Actions CI | — | ✅ Reviewed | 1 |
| data/corpus.json | PDF manifest (URLs updated 2026-05-02) | — | ✅ Reviewed | 1 |
| src/ingestion/downloader.py | PDF Downloader (browser UA header) | download_corpus | ✅ Reviewed | 1 |
| src/ingestion/extractor.py | PDF Text Extractor | extract_pages, extract_corpus | ✅ Reviewed | 1 |
| src/ingestion/chunker.py | Sentence-boundary chunker | detect_section, chunk_text, chunk_document, save_chunks | ✅ Reviewed | 1 |
| src/retrieval/base.py | Abstract base + TypedDicts | Chunk, RetrievalResult, BaseRetriever, timed_retrieve | ✅ Reviewed | 1 |
| src/evaluation/logger.py | SQLite eval logger | init_db, log_row, fetch_all, fetch_run | ✅ Reviewed | 1 |
| src/retrieval/dense.py | Dense FAISS Retriever (L2-normalize + IndexFlatIP) | DenseRetriever | ✅ Reviewed | 2 |
| src/retrieval/bm25.py | BM25 Retriever (BM25Okapi, pickle) | BM25Retriever | ✅ Reviewed | 2 |
| src/retrieval/hybrid.py | Hybrid Dense+BM25+CrossEncoder | HybridRetriever | ✅ Reviewed | 2 |
| src/retrieval/tree_index.py | LlamaIndex Tree Index (Groq primary, Gemini fallback) | TreeIndexRetriever | ✅ Reviewed | 2 |
| src/generation/__init__.py | Generation module init | — | ✅ Reviewed | 3 |
| src/generation/generator.py | LLM Answer Generator (Groq/Gemini, lazy imports) | generate, generate_from_env | ✅ Reviewed | 3 |
| src/evaluation/ragas_runner.py | RAGAS 0.4 runner (instructor-patched Groq, HFEmbeddings) | run_ragas, run_ragas_from_env | ✅ Reviewed | 3 |
| src/evaluation/ragas_runner.py note | Returns answer_relevancy→answer_relevance to match EvalRow contract | — | — | 3 |
| scripts/ingest.py | Ingestion pipeline CLI | — | ✅ Reviewed | 1 |
| scripts/build_indexes.py | Index building CLI | — | ✅ Reviewed | 2 |
| scripts/run_eval.py | Eval pipeline CLI (cost guard, --limit, --strategies) | — | ✅ Reviewed | 3 |
| data/eval/questions.json | 50 eval questions — 10 need replacement (see ground_truth_review.md) | — | ⚠️ Needs update | 3 |
| data/eval/ground_truth.json | Ground truth stubs — empty until user approves review doc | — | ⚠️ Awaiting review | 3 |
| data/eval/ground_truth_review.md | Ground truths extracted from PDFs + page citations for user review | — | ⚠️ Needs user review | 3 |
| docs/chunking_analysis.md | Chunking strategy, corpus stats, weaknesses, eval hypotheses | — | ✅ Complete | 3 |
| tests/fixtures/sample_pages.py | Synthetic test corpus | SAMPLE_PAGES | ✅ Reviewed | 1 |
| tests/conftest.py | Load .env at pytest collection time | — | ✅ Reviewed | 2 |
| tests/test_ingestion.py | Chunker unit tests (10 tests) | — | ✅ Reviewed | 1 |
| tests/test_retrieval.py | Retrieval contract tests | — | ✅ Reviewed | 1 |
| tests/test_retrieval_strategies.py | Phase 2 retriever unit tests | — | ✅ Reviewed | 2 |
| tests/test_eval.py | Phase 3 eval pipeline unit tests (5 tests) | — | ✅ Reviewed | 3 |
| notebooks/exploration.ipynb | Chunk quality inspection | — | ✅ Reviewed | 1 |
| src/api/main.py | FastAPI backend app | FastAPI app | ✅ Implemented | 4 |
| src/api/static/index.html | HTML/JS Chat Frontend | — | ✅ Implemented | 4 |
| src/api/__init__.py | API package init | — | ✅ Reviewed | 4 |
| Procfile | Deployment start command for Railway | — | ✅ Reviewed | 4 |
| railway.json | Railway build/deploy config (healthcheckTimeout=300) | — | ✅ Reviewed | 4 |
| nixpacks.toml | Nixpacks build phase — pre-downloads sentence-transformers models | — | ✅ Reviewed | 4 |
| scripts/preload_models.py | Pre-downloads all-MiniLM-L6-v2 + cross-encoder at build time | — | ✅ Reviewed | 4 |

---

## Interface Contracts — do not change without cascading updates

```
Chunk           = {id: str, text: str, doc_id: str, page: int, section: str}
RetrievalResult = {strategy: str, chunks: List[Chunk], latency_ms: float, token_cost: int}
EvalRow         = {query_id: str, strategy: str, context_precision: float, context_recall: float,
                   faithfulness: float, answer_relevance: float, latency_ms: float, token_cost: int}
```

Note: RAGAS 0.4 returns key `answer_relevancy`; ragas_runner.py maps it to `answer_relevance` before returning.

---

## Dependency Map

```
data/corpus.json → downloader.py → data/raw/<doc_id>.pdf
                                 → extractor.py → data/processed/<doc_id>.json
                                               → chunker.py → data/chunks/<doc_id>_chunks.json
                                                            → build_indexes.py → data/indexes/*
data/indexes/* + data/eval/questions.json + data/eval/ground_truth.json
    → scripts/run_eval.py → results/evals.db
    → src/generation/generator.py (Groq 70B → answer)
    → src/evaluation/ragas_runner.py (Groq 70B → RAGAS scores)
    → src/evaluation/logger.py (SQLite write)

[Phase 4]
data/indexes/* → FastAPI backend (src/api/main.py) → HTML/JS frontend
results/evals.db → FastAPI /results endpoint → charts tab
```

---

## Review Status

| File | Verdict | Security | Notes |
|------|---------|----------|-------|
| src/ingestion/downloader.py | ✅ | ✅ | Browser UA added for RBI CDN |
| src/ingestion/extractor.py | ✅ | ✅ | — |
| src/ingestion/chunker.py | ✅ | ✅ | Infinite-loop edge case fixed; known weakness: footnote noise |
| src/retrieval/base.py | ✅ | ✅ | — |
| src/retrieval/dense.py | ✅ | ✅ | O(1) index lookup; L2-normalize + IndexFlatIP |
| src/retrieval/bm25.py | ✅ | ✅ | Local pickle only |
| src/retrieval/hybrid.py | ✅ | ✅ | Dedup by chunk id; local CrossEncoder |
| src/retrieval/tree_index.py | ✅ | ✅ | Lazy imports; Groq primary, Gemini fallback |
| src/evaluation/logger.py | ✅ | ✅ | All SQL parameterized |
| src/generation/generator.py | ✅ | ✅ | Lazy imports; keys from env only |
| src/evaluation/ragas_runner.py | ✅ | ✅ | RAGAS 0.4; instructor-patched Groq; lazy imports |
| scripts/run_eval.py | ✅ | ✅ | Cost guard mandatory; per-row error isolation |
| tests/ | ✅ | ✅ | 33 passed, 0 skipped |
