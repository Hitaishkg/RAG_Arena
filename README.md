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
| **Dense** | Semantic similarity via FAISS + `all-MiniLM-L6-v2` | Conceptual / paraphrased queries |
| **Hybrid** | BM25 + Dense fused, re-ranked by cross-encoder | General Q&A — best overall recall |
| **Tree Index** | LlamaIndex hierarchical summary tree (Gemini) | Keyword factoids — highest precision |

---

## Evaluation Results

41 hand-crafted questions × 4 strategies = **164 eval rows** (RAGAS 0.4.3)

| Strategy | Precision | Recall | Faithfulness | Ans. Relevance | Latency |
|----------|:---------:|:------:|:------------:|:--------------:|:-------:|
| BM25 | 0.036 | 0.274 | **0.932** | 0.551 | **21ms** |
| Dense | 0.073 | 0.203 | 0.864 | 0.422 | 62ms |
| Hybrid | 0.059 | **0.284** | 0.913 | **0.580** | 822ms |
| Tree Index | **0.100** | 0.187 | 0.929 | 0.468 | 20,828ms |

**Key findings:**
- **Hybrid** wins on recall and answer relevance — best general-purpose strategy
- **BM25** punches above its weight: beats dense on recall at 21ms latency
- **Tree Index** achieves 0.375 precision on keyword queries (4× others) but 0 on multi-hop
- **Dense** underperforms — general embeddings not tuned to regulatory language
- 34/41 questions score 0 context precision across ALL strategies — RAGAS precision is strict; recall is the meaningful signal

Full breakdown in [`findings.md`](findings.md).

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
        Dense FAISS (all-MiniLM-L6-v2)
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
│   └── evals.db         # RAGAS eval results (run_12d94e65)
├── findings.md          # Eval analysis + strategy selection guide
├── Dockerfile
└── requirements.txt
```

---

## License

MIT
