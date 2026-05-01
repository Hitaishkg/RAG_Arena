# RAG Arena — Claude Code Instructions

## What this project is

A 4-way RAG retrieval benchmarking system that runs the same query through four retrieval strategies (Dense, BM25, Tree Index, Hybrid), evaluates each on 6 metrics (4 RAGAS quality + latency + token cost), and presents results on a live Streamlit dashboard.

**This is not a chatbot.** It is an evaluation framework. The RAG component exists to be measured.

**Target domain:** RBI and SEBI regulatory PDFs — long-form, hierarchically structured documents.

Full specification: `rag-arena-spec.md` (project root). Read it before doing anything non-trivial.

---

## Read order for any new task

1. `rag-arena-spec.md` — understand intent and constraints
2. `CODEBASE_GRAPH.md` — understand current state of source files (do not read source files without checking this first)
3. Only then load the specific source files relevant to the task

---

## Development Workflow — Multi-Agent Structure

Five agent roles. Only one is active at a time. Default role: **Coder**.

| Role | Reads | Produces | Does NOT |
|------|-------|----------|----------|
| Architect | spec + graph | Task list for current phase | Write code |
| Coder | task list + graph + relevant files | Implementation, one file at a time | Review own output |
| Reviewer | changed file + spec + graph | Inline comments + updated graph | Fix code |
| Security | all phase changes | Security report | Fix code |
| Documenter | graph + changed files + spec §13 | README update + commit + push | — |

Switch role by user instruction: "act as architect / reviewer / security / documenter"

### Workflow loop per phase

```
1. Architect → task list
2. Coder → writes one file
3. Reviewer → approves or returns to Coder with specific instructions
   → updates CODEBASE_GRAPH.md on approval
4. repeat 2–3 for each task
5. Security → scans all phase changes
6. Documenter → README update + commit (feat(phase-N): <what was built>)
```

Use worktree isolation for Coder on each phase. Run `simplify` skill after Reviewer approval, before Security.

---

## Implementation Phases

### Phase 1 — Foundation (data pipeline + shared infrastructure)
- Project structure, venv, `.env`
- `ingestion/downloader.py`, `ingestion/extractor.py`, `ingestion/chunker.py`
- `scripts/ingest.py` end-to-end
- `retrieval/base.py` abstract Retriever class
- `evaluation/logger.py` SQLite schema
- `tests/` skeleton + fixture corpus (5 pages)
- Exit: `scripts/ingest.py` runs clean, chunks inspectable, base class defined

### Phase 2 — Retrieval Pipelines
- `retrieval/dense.py` — FAISS + `all-MiniLM-L6-v2`
- `retrieval/bm25.py` — rank-bm25
- `retrieval/tree_index.py` — LlamaIndex TreeIndex + Gemini
- `retrieval/hybrid.py` — Dense + BM25 parallel + cross-encoder reranker
- `scripts/build_indexes.py`
- Exit: all 4 retrievers pass unit tests, return shared schema

### Phase 3 — Generation + Evaluation Loop
- `generation/generator.py` — Gemini Flash primary, Groq fallback
- `evaluation/ragas_runner.py` — RAGAS dataset + 4 metrics
- `evaluation/operational.py` — latency timer, token cost
- `scripts/run_eval.py` — 50 questions × 4 strategies → 200 rows in DB
- Exit: `results/evals.db` contains 200 rows, all 6 metrics populated

### Phase 4 — Dashboard
- `dashboard/app.py` + components: query_runner, comparison, aggregate, drilldown
- Exit: `streamlit run dashboard/app.py` functional, live query under 5s for Dense/BM25/Hybrid

### Phase 5 — Findings + Documentation
- `scripts/export_findings.py` → `results/findings.md` + `results/summary.csv`
- `README.md` with findings, architecture diagram, setup instructions
- 2-minute screen recording demo
- `v1.0.0` GitHub release

---

## Interface Contracts — Do Not Change Without Updating All Dependents

```python
Chunk           = {id: str, text: str, doc_id: str, page: int, section: str}
RetrievalResult = {strategy: str, chunks: List[Chunk], latency_ms: float, token_cost: int}
EvalRow         = {query_id: str, strategy: str, context_precision: float,
                   context_recall: float, faithfulness: float,
                   answer_relevance: float, latency_ms: float, token_cost: int}
```

---

## Hard Rules

- **Never hardcode API keys.** All secrets via `.env` + `python-dotenv`.
- **Never change interface contracts** in `CODEBASE_GRAPH.md` without updating all dependent files.
- **Every file you create or modify:** update `CODEBASE_GRAPH.md` File Registry before stopping.
- **Generation model must be identical** across all 4 retrieval strategies in any single eval run. The only variable being tested is retrieval.
- **Do not generate ground truth answers with an LLM.** `data/eval/ground_truth.json` is hand-written only. LLM-generated ground truth makes RAGAS Context Recall scores circular.
- **Use `all-MiniLM-L6-v2` (local) for Dense embeddings** — not OpenAI embeddings. Keeps project runnable without paid API access.
- **Tree Index is expensive** (~$0.01–$0.05/query). Add a cost guard in `run_eval.py` that prints estimated cost and asks for confirmation before running Tree Index on the full eval set.
- **Hybrid reranker is a cross-encoder**, not a bi-encoder. Score (query, chunk) pairs jointly. This distinction matters for interviews.

---

## LLM Role Assignment

| Role | Primary | Fallback |
|------|---------|----------|
| RAG answer generation | Gemini 1.5 Flash | Groq / Llama 3.3 70B |
| RAGAS judge | Gemini 1.5 Flash | Groq / Llama 3.3 70B |
| Tree Index node summarisation | Gemini 1.5 Flash | Groq / Llama 3.3 70B |
| Embeddings | `all-MiniLM-L6-v2` (local) | — |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) | — |

Fallback trigger: Gemini call fails or hits rate limit → retry once → fall back to Groq.

---

## Tech Stack

Python 3.11+ | pdfplumber | FAISS + sentence-transformers | rank-bm25 | llama-index-core | llama-index-llms-gemini | ragas | streamlit | sqlite3 + pandas | pytest | python-dotenv | uv (package manager)

---

## Key Out-of-Scope Items

No authentication, no document upload UI, no fine-tuned embeddings, no streaming responses, no cloud deployment, no non-PDF formats.

---

## Quick Commands (Makefile)

```bash
make ingest          # scripts/ingest.py
make build-indexes   # scripts/build_indexes.py
make eval            # scripts/run_eval.py
make dashboard       # streamlit run dashboard/app.py
make test            # pytest tests/ -v
make findings        # scripts/export_findings.py
```

---

## CODEBASE_GRAPH.md

Maintained at project root. Every agent reads this before reading source files. Every agent updates this after creating or modifying a file. Format: File Registry + Interface Contracts + Dependency Map + Review Status. See `rag-arena-spec.md` Section 16 for full format.
