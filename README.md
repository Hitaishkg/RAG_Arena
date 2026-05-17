# RAG Arena

**A 4-strategy Retrieval-Augmented Generation benchmark over Indian financial regulatory corpus.**

Live demo → **[rag-arena-322804211543.asia-south1.run.app](https://rag-arena-322804211543.asia-south1.run.app/static/index.html)**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![GCP](https://img.shields.io/badge/GCP-Cloud%20Run-4285F4?logo=googlecloud&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What is this?

RAG Arena runs the same question simultaneously through **4 retrieval strategies** and lets you compare answers, latency, and source chunks side by side — all in the browser.

The corpus is 5 SEBI regulations (1,367 chunks, ~891 pages). Every strategy retrieves from the same chunked corpus; only the retrieval mechanism differs.

---

## Retrieval Strategies

| Strategy | How it works | Best for |
|----------|-------------|----------|
| **BM25** | Sparse keyword matching (TF-IDF variant) | Exact terms, regulation numbers, speed |
| **Dense** | Semantic similarity via FAISS + embedding model | Conceptual / paraphrased queries |
| **Hybrid** | BM25 + Dense fused, re-ranked by cross-encoder | General Q&A — best overall recall |
| **Tree Index** | LlamaIndex hierarchical summary tree (Gemini) | Cross-topic compound queries — highest precision |

---

## Evaluation Results

41 hand-crafted questions across 4 categories (keyword, semantic, multihop, compound) × 4 strategies. Scored with RAGAS 0.4.3.

### Run 1 — `run_12d94e65` (2026-05-03) · baseline encoder

| Strategy | Precision | Recall | Faithfulness | Ans. Relevance | Latency |
|----------|:---------:|:------:|:------------:|:--------------:|:-------:|
| BM25 | 0.036 | 0.274 | **0.932** | 0.551 | **21ms** |
| Dense | 0.073 | 0.203 | 0.864 | 0.422 | 62ms |
| Hybrid | 0.059 | **0.284** | 0.913 | **0.580** | 822ms |
| Tree Index | **0.100** | 0.187 | 0.929 | 0.468 | 20,828ms |

### Run 2 — `run_023c3905` (2026-05-17) · upgraded encoder

| Strategy | Precision | Recall | Faithfulness | Ans. Relevance | Latency |
|----------|:---------:|:------:|:------------:|:--------------:|:-------:|
| BM25 | 0.149 | 0.296 | **0.911** | 0.744 | **57ms** |
| Dense | 0.252 | 0.227 | **0.953** | 0.765 | 92ms |
| Hybrid | 0.170 | **0.300** | 0.924 | **0.808** | 717ms |
| Tree Index | **0.263** | 0.188 | 0.814 | 0.648 | 11,205ms |

### What changed between runs

The only variable changed between Run 1 and Run 2 was the **embedding model** used for Dense and Hybrid retrieval. The generator, RAGAS scorer, corpus, questions, and ground truth were identical.

| Metric | Impact |
|--------|--------|
| Context Precision | +0.11 to +0.18 across all strategies |
| Answer Relevance | +0.18 to +0.34 across all strategies |
| Tree Index latency | 20,828ms → 11,205ms (encoder faster at inference) |
| Hybrid latency | 822ms → 717ms |

The encoder is upstream of every strategy. A better embedding model lifted all four strategies simultaneously — the largest single improvement observed across the project.

### Per-category winners (Run 2)

| Question type | Best strategy | Why |
|---------------|--------------|-----|
| Keyword (exact lookups) | **BM25** | Highest recall (0.563), fastest (57ms) |
| Semantic (conceptual) | **Dense** (precision) / **Hybrid** (answer quality) | Dense embeds concepts best; Hybrid generates best answers |
| Multihop (two-part) | **Hybrid** | Best recall (0.304) and answer relevance (0.840) |
| Compound (cross-regulation) | **Tree Index** (retrieval) + **Dense** (answer) | Tree's hierarchy spans multiple branches; Dense generates best answers |

**Key findings:**
- **Hybrid** wins overall — best recall and answer relevance across both runs
- **BM25** beats dense on recall at a fraction of the latency; strong on keyword queries
- **Tree Index** surprisingly leads precision and recall on compound (cross-regulation) questions — its hierarchical structure navigates multi-topic queries well
- **Faithfulness is uniformly high (0.81–0.95)** — the generation model stays grounded in retrieved context regardless of retrieval quality; the bottleneck is retrieval, not hallucination
- **34/41 questions score 0 context precision across all strategies** — RAGAS precision is strict; recall is the more informative signal for this corpus

Full breakdown with per-category tables and methodology notes in [`findings.md`](findings.md).

---

## Corpus

| Regulation | Full Name | Chunks |
|------------|-----------|--------|
| SEBI ICDR 2018 | Issue of Capital & Disclosure Requirements | 700 |
| SEBI LODR 2015 | Listing Obligations & Disclosure Requirements | 173 |
| SEBI Mutual Fund Reg | SEBI (Mutual Funds) Regulations | 291 |
| SEBI PIT 2015 | Prohibition of Insider Trading | 99 |
| SEBI SAST 2011 | Substantial Acquisition of Shares & Takeovers | 104 |
| **Total** | | **1,367** |

---

## Architecture

```
PDF Corpus (5 SEBI docs)
    → pdfplumber extractor → sentence-boundary chunker
    → 4 indexes built offline:
        BM25 (rank-bm25)
        Dense FAISS (embedding model)
        Hybrid (BM25 + Dense + cross-encoder reranker)
        Tree Index (LlamaIndex + Gemini leaf summarisation)

Query (runtime)
    → FastAPI /query endpoint
    → concurrent.futures: all 4 strategies in parallel
    → LLM answer generation (Groq llama-3.3-70b / Gemini 2.5 Flash Lite)
    → 4 results returned simultaneously to frontend

Eval pipeline (offline)
    → 41 questions × 4 strategies
    → RAGAS 0.4.3: context precision, recall, faithfulness, answer relevance
    → results stored in results/evals.db → /results tab charts
```

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Retrieval | FAISS, rank-bm25, LlamaIndex, sentence-transformers |
| Reranking | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Generation | Groq (llama-3.3-70b-versatile), Google Gemini 2.5 Flash Lite |
| Evaluation | RAGAS 0.4.3 |
| Backend | FastAPI, uvicorn |
| Frontend | Vanilla HTML/JS, Chart.js |
| Deployment | GCP Cloud Run (asia-south1), Docker |
| Infra | Secret Manager, Artifact Registry, Cloud Build |

---

## Running Locally

```bash
# 1. Clone and set up
git clone https://github.com/Hitaishkg/RAG_Arena.git
cd RAG_Arena
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env   # add GROQ_API_KEY + GOOGLE_API_KEY

# 3. Start the API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 4. Open in browser
open http://localhost:8000/static/index.html
```

Indexes and chunks are pre-built and committed — no ingestion step needed for local dev.

---

## Running the Eval Pipeline

```bash
# Full eval (41 questions × 4 strategies) — needs GOOGLE_API_KEY
GENERATION_PROVIDER=gemini GEMINI_MODEL=gemini-2.0-flash \
  python scripts/run_eval.py --db results/evals.db
```

> Cost: ~$0.25 with Gemini 2.0 Flash. Set `GEMINI_MODEL=gemini-2.0-flash` to avoid thinking token charges.  
> After a new eval run, update `ACTIVE_RUN_ID` in `src/api/main.py` to point the UI at the new results.

---

## Project Structure

```
rag_arena/
├── src/
│   ├── ingestion/       # PDF download, text extraction, chunking
│   ├── retrieval/       # BM25, Dense, Hybrid, Tree Index retrievers
│   ├── generation/      # LLM answer generator (Groq + Gemini)
│   ├── evaluation/      # RAGAS runner + SQLite logger
│   └── api/             # FastAPI app + static frontend
├── scripts/             # CLI: ingest, build_indexes, run_eval, preload_models
├── data/
│   ├── chunks/          # Pre-chunked corpus (1,367 chunks)
│   ├── indexes/         # Pre-built indexes (BM25, FAISS, Tree)
│   └── eval/            # Questions + hand-written ground truths
├── results/
│   └── evals.db         # RAGAS eval results (run_12d94e65, run_023c3905)
├── findings.md          # Eval analysis + per-category breakdown + strategy guide
├── Dockerfile
└── requirements.txt
```

---

## License

MIT
