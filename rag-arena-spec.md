# RAG Arena — Project Specification

> **Purpose of this document:** Single source of truth for the RAG Arena project. Used by Claude Code, Gemini CLI, and any contributor to understand what is being built, why, and how. All implementation decisions must trace back to this spec.

---

## 1. What We Are Building

**RAG Arena** is a benchmarking system that runs the same natural language query through four distinct RAG retrieval strategies, evaluates each using standardized metrics, and presents a side-by-side comparison on a live dashboard.

The system answers a real engineering question:

> *"Which retrieval strategy is best for a given document corpus and query type — and is the quality premium of more expensive strategies worth the cost and latency trade-off?"*

This is not a chatbot. It is an evaluation and comparison framework. The RAG component exists to be measured, not to be the product.

---

## 2. Problem Statement & Motivation

Most teams building RAG systems make a default choice — usually vector search — without benchmarking alternatives. This leads to:

- Overpaying for embedding APIs when BM25 would perform equally well on keyword-heavy queries
- Underutilising tree-based retrieval on long, hierarchically structured documents
- No quantitative basis for choosing between strategies when requirements change

RAG Arena solves this by running all four major retrieval paradigms on the same corpus and queries, measuring quality, cost, and latency, and surfacing the trade-offs in a format that drives decisions.

**Target domain:** RBI (Reserve Bank of India) and SEBI (Securities and Exchange Board of India) regulatory documents. These are publicly available, long-form, hierarchically structured PDFs — an ideal stress test for all four strategies.

---

## 3. The Four Retrieval Strategies

Each strategy operates as an independent, swappable module. They share the same document corpus, the same LLM for generation, and the same evaluation pipeline. The only variable is how they retrieve context.

### 3.1 Dense Retrieval (Vector Search)
- Documents are chunked and embedded using a sentence-transformer model
- Chunks are stored in a FAISS index
- At query time, the query is embedded and the top-k nearest neighbours are retrieved by cosine similarity
- Strengths: handles paraphrased questions, semantic similarity
- Weaknesses: poor on exact keyword matching, requires embedding infrastructure

### 3.2 Sparse Retrieval (BM25 / Keyword)
- Documents are chunked and indexed using BM25 (Best Match 25) — a probabilistic keyword ranking algorithm
- No embeddings. No LLM at retrieval time.
- At query time, query terms are matched against the inverted index by term frequency and inverse document frequency
- Strengths: fast, cheap, exact keyword matching, no API dependency
- Weaknesses: no semantic understanding, fails on paraphrased queries

### 3.3 Tree Index Retrieval
- Documents are chunked into leaf nodes
- An LLM builds a summary tree bottom-up: leaf summaries → parent summaries → root summary
- At query time, the tree is traversed top-down: the LLM reads each node's summary and decides which branch is relevant, repeating until a leaf is reached
- No vector embeddings. Retrieval is LLM-guided.
- Strengths: structure-aware, handles long documents with hierarchical organisation (chapters, sections, clauses), good at multi-hop questions
- Weaknesses: expensive (multiple LLM calls per query), slow, overkill for short documents

### 3.4 Hybrid Retrieval (Dense + BM25 + Reranker)
- Dense and BM25 retrieval run in parallel on the same query
- Results from both are merged and passed through a cross-encoder reranker that scores each chunk against the query directly
- Top-k reranked chunks are passed to the LLM for generation
- Strengths: combines semantic and keyword signals, highest recall, most robust
- Weaknesses: highest latency and cost of the four strategies

---

## 4. Evaluation Metrics

Every query run through every strategy is scored on six metrics. Four are quality metrics from the RAGAS framework. Two are operational.

### 4.1 Quality Metrics (RAGAS)

| Metric | What it measures | How it is computed |
|---|---|---|
| **Context Precision** | Of the chunks retrieved, what fraction are actually relevant to the query? | LLM-as-judge scores each retrieved chunk for relevance |
| **Context Recall** | Of all relevant information in the corpus, what fraction was retrieved? | Compares retrieved context against ground-truth answer |
| **Faithfulness** | Does the generated answer stay within the retrieved context? Hallucination detector. | LLM checks if every claim in the answer is supported by the context |
| **Answer Relevance** | Does the generated answer actually address the question asked? | Embedding similarity between question and answer |

All four scores are in [0, 1]. Higher is better.

### 4.2 Operational Metrics

| Metric | Unit | Why it matters |
|---|---|---|
| **Latency** | milliseconds per query | Tree index and hybrid are significantly slower — quantify the cost |
| **Token cost** | tokens per query (input + output) | BM25 uses zero retrieval tokens; tree index uses many |

### 4.3 Evaluation Dataset

A curated set of 30–50 question-answer pairs derived from the RBI/SEBI document corpus. Categories:

- **Exact keyword queries** — "What is the minimum capital requirement for a payment aggregator?" (BM25 expected to win)
- **Semantic / paraphrased queries** — "What rules apply when a bank wants to invest in another company?" (Dense expected to win)
- **Multi-hop / hierarchical queries** — "What are the conditions under which a NBFC can accept public deposits, and what are the disclosure requirements?" (Tree Index expected to win)
- **Complex compound queries** — multi-part questions requiring broad recall (Hybrid expected to win)

This split is intentional — each strategy should have a query type where it is expected to lead, making the comparison meaningful rather than one strategy dominating across the board.

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   DATA INGESTION                     │
│  PDF download → pdfplumber extract → chunk → store  │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────┴──────┐ ┌──────┴──────┐ ┌─────┴────────┐
│ FAISS Index  │ │ BM25 Index  │ │  Tree Index  │
│ (embeddings) │ │  (rank-bm25)│ │  (LlamaIndex)│
└───────┬──────┘ └──────┬──────┘ └─────┬────────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
              ┌─────────┴──────────┐
              │   HYBRID RERANKER  │
              │  (Dense + BM25 +   │
              │   cross-encoder)   │
              └─────────┬──────────┘
                        │
              ┌─────────┴──────────┐
              │    LLM GENERATION  │
              │  (Gemini / OpenAI) │
              └─────────┬──────────┘
                        │
              ┌─────────┴──────────┐
              │   RAGAS EVAL LOOP  │
              │  (score all 4 per  │
              │   query, log to DB)│
              └─────────┬──────────┘
                        │
              ┌─────────┴──────────┐
              │  STREAMLIT DASHBOARD│
              │  side-by-side view  │
              └────────────────────┘
```

---

## 6. Project Structure

```
rag-arena/
├── data/
│   ├── raw/                    # downloaded RBI/SEBI PDFs (gitignored)
│   ├── processed/              # chunked text, serialised
│   │   ├── chunks.jsonl        # one chunk per line: {id, text, source, page}
│   │   └── metadata.json       # doc registry
│   └── eval/
│       ├── questions.json      # 50 eval questions with category tags
│       └── ground_truth.json   # expected answers for RAGAS recall scoring
│
├── src/
│   ├── ingestion/
│   │   ├── downloader.py       # fetch PDFs from RBI/SEBI URLs
│   │   ├── extractor.py        # pdfplumber → raw text per page
│   │   └── chunker.py          # fixed-size + sentence-boundary chunking
│   │
│   ├── retrieval/
│   │   ├── base.py             # abstract Retriever class (retrieve(query, k) → List[Chunk])
│   │   ├── dense.py            # FAISS + sentence-transformers
│   │   ├── bm25.py             # rank-bm25 wrapper
│   │   ├── tree_index.py       # LlamaIndex TreeIndex wrapper
│   │   └── hybrid.py           # Dense + BM25 fusion + cross-encoder reranker
│   │
│   ├── generation/
│   │   └── generator.py        # LLM wrapper (Gemini/OpenAI), prompt template, token counting
│   │
│   ├── evaluation/
│   │   ├── ragas_runner.py     # runs RAGAS dataset evaluation, returns scores dict
│   │   ├── operational.py      # latency timer, token cost calculator
│   │   └── logger.py           # writes results to SQLite (results/evals.db)
│   │
│   └── dashboard/
│       ├── app.py              # Streamlit entry point
│       ├── components/
│       │   ├── query_runner.py # UI: input query → run all 4 → display results
│       │   ├── comparison.py   # side-by-side metric table
│       │   ├── aggregate.py    # charts: avg scores, cost vs quality scatter
│       │   └── drilldown.py    # per-query breakdown, retrieved chunks inspector
│       └── data_loader.py      # reads from results/evals.db
│
├── results/
│   ├── evals.db                # SQLite: all eval runs (gitignored, large)
│   └── summary.csv             # aggregate findings export
│
├── notebooks/
│   └── exploration.ipynb       # corpus exploration, chunk quality checks
│
├── tests/
│   ├── test_retrieval.py       # unit tests for each retriever
│   ├── test_eval.py            # eval pipeline correctness
│   └── fixtures/               # small test corpus (5 pages)
│
├── scripts/
│   ├── ingest.py               # CLI: run full ingestion pipeline
│   ├── build_indexes.py        # CLI: build all 4 indexes from processed chunks
│   ├── run_eval.py             # CLI: run full eval suite, write to DB
│   └── export_findings.py      # CLI: generate summary.csv + findings.md
│
├── .env.example                # OPENAI_API_KEY, GOOGLE_API_KEY, etc.
├── requirements.txt
├── README.md
└── SPEC.md                     # this file
```

---

## 7. Tech Stack

| Component | Library / Tool | Reason |
|---|---|---|
| PDF extraction | `pdfplumber` | Better table/layout handling than PyMuPDF for regulatory docs |
| Chunking | custom + `nltk` | Sentence-boundary aware, configurable overlap |
| Dense index | `faiss-cpu`, `sentence-transformers` | `all-MiniLM-L6-v2` — local, zero API cost |
| Sparse index | `rank-bm25` | Lightweight, no server needed |
| Tree index | `llama-index-core`, `llama-index-llms-gemini` | Built-in `TreeIndex`, native Gemini integration |
| Hybrid reranker | `sentence-transformers` cross-encoder | `cross-encoder/ms-marco-MiniLM-L-6-v2` — local, zero API cost |
| LLM — primary | `google-generativeai` / Gemini 1.5 Flash | Cheap, fast, available via free API key |
| LLM — fallback | `groq` / Llama 3.3 70B | Free tier, very fast inference, rate limit safety net |
| Evaluation | `ragas` | Standard RAG eval framework, LLM-as-judge |
| Result storage | `sqlite3` + `pandas` | Zero infra, portable, queryable |
| Dashboard | `streamlit` | Fast to build, live interactive demo |
| Testing | `pytest` | Unit tests for retrieval correctness |
| Environment | `python-dotenv` | API key management |

**Python version:** 3.11+

### LLM Role Assignment

| Role | Primary | Fallback | Notes |
|---|---|---|---|
| Query generation (RAG answer) | Gemini 1.5 Flash | Groq / Llama 3.3 70B | Same model across all 4 strategies — generation must be held constant |
| RAGAS judge (eval scoring) | Gemini 1.5 Flash | Groq / Llama 3.3 70B | Consistent judge model gives consistent scores across runs |
| Tree Index node summarization | Gemini 1.5 Flash | Groq / Llama 3.3 70B | High call volume during index build — Flash keeps cost low |
| Embeddings | `all-MiniLM-L6-v2` (local) | — | No API cost, runs on CPU |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) | — | No API cost, runs on CPU |

**Fallback trigger:** If a Gemini call fails or hits a rate limit, the `generation/generator.py` wrapper automatically retries once, then falls back to Groq. This is the same pattern used in the Indian Trader project (multi-LLM fallback chains).

---

## 8. Dashboard Specification

The Streamlit dashboard has four views:

### 8.1 Live Query Runner
- Text input field for a natural language question
- "Run All Strategies" button
- Triggers all 4 retrievers + generation in sequence (or parallel with threading)
- Displays a result card per strategy showing: retrieved chunks, generated answer, all 6 metrics

### 8.2 Side-by-Side Comparison Table
```
Query: "What is the minimum capital requirement for a payment aggregator?"
Category: Exact keyword

┌─────────────────┬────────────┬────────────┬──────────────┬───────────┐
│ Metric          │ Dense      │ BM25       │ Tree Index   │ Hybrid    │
├─────────────────┼────────────┼────────────┼──────────────┼───────────┤
│ Ctx Precision   │ 0.72       │ 0.91       │ 0.85         │ 0.89      │
│ Ctx Recall      │ 0.81       │ 0.68       │ 0.88         │ 0.90      │
│ Faithfulness    │ 0.94       │ 0.88       │ 0.92         │ 0.95      │
│ Answer Relevance│ 0.87       │ 0.90       │ 0.86         │ 0.91      │
│ Latency (ms)    │ 210        │ 45         │ 2800         │ 390       │
│ Token cost      │ 620        │ 380        │ 2100         │ 950       │
├─────────────────┼────────────┼────────────┼──────────────┼───────────┤
│ WINNER          │            │ ✅ Quality  │              │ ✅ Recall  │
└─────────────────┴────────────┴────────────┴──────────────┴───────────┘
```

### 8.3 Aggregate Analytics
- Bar charts: average score per metric per strategy across all 50 eval queries
- Scatter plot: quality (avg RAGAS) vs cost (avg tokens) — one dot per strategy
- Breakdown by query category (keyword / semantic / multi-hop / compound)
- Headline finding surfaced automatically: "BM25 matches Dense quality on keyword queries at 5x lower cost"

### 8.4 Chunk Inspector / Drilldown
- Select any past query from a dropdown
- See the exact chunks each strategy retrieved
- Highlight overlap and differences between strategies
- Useful for understanding why a strategy won or lost on a specific query

---

## 9. Data Pipeline

### 9.1 Document Corpus
- Source: RBI Master Circulars and SEBI Regulations (public PDFs)
- Target: 10–15 documents, 500–1500 pages total
- Download script: `scripts/ingest.py` handles fetch → extract → chunk → save

### 9.2 Chunking Strategy
- Chunk size: 512 tokens with 64-token overlap
- Boundary: sentence-aware (do not cut mid-sentence)
- Metadata per chunk: `{doc_id, page_number, section_header, char_start, char_end}`
- Tree Index uses the same chunks as leaf nodes — no separate chunking needed

### 9.3 Evaluation Set Construction
- 50 questions hand-curated from the corpus
- 12–13 per category: keyword, semantic, multi-hop, compound
- Ground truth answers written from the source document, not from any model
- Stored in `data/eval/questions.json` and `data/eval/ground_truth.json`

---

## 10. Implementation Phases

### Phase 1 — Foundation
**Goal:** Working data pipeline and shared infrastructure that all four retrieval strategies will plug into.

- Set up project structure, virtual environment, `.env` configuration
- Implement PDF downloader and extractor (`ingestion/downloader.py`, `ingestion/extractor.py`)
- Implement chunker with sentence-boundary awareness and metadata tagging
- Write and run `scripts/ingest.py` end-to-end on the full corpus
- Verify chunk quality in `notebooks/exploration.ipynb` (distribution of lengths, no truncated sentences, section headers captured)
- Define the `Retriever` abstract base class in `retrieval/base.py`
- Define the result schema (what a retrieval run returns: chunks, latency, token count)
- Set up SQLite schema in `evaluation/logger.py`
- Write fixture corpus (5 pages) and skeleton tests in `tests/`

**Exit criteria:** `scripts/ingest.py` runs clean, chunks are inspectable, base class is defined.

---

### Phase 2 — Retrieval Pipelines
**Goal:** All four retrieval strategies implemented, independently testable, returning results in the shared schema.

- **Dense** (`retrieval/dense.py`): embed chunks with `all-MiniLM-L6-v2`, build FAISS flat index, implement `retrieve(query, k=5)`, serialise index to disk
- **BM25** (`retrieval/bm25.py`): build `BM25Okapi` index from tokenised chunks, implement `retrieve(query, k=5)`, serialise to disk
- **Tree Index** (`retrieval/tree_index.py`): use LlamaIndex `TreeIndex` with Gemini as the node LLM, wrap `retrieve(query)` to return leaf chunks + traversal path
- **Hybrid** (`retrieval/hybrid.py`): run Dense and BM25 in parallel, merge top-k candidates, rerank with `cross-encoder/ms-marco-MiniLM-L-6-v2`, return top-5 reranked chunks
- Write `scripts/build_indexes.py` to build and serialise all four indexes from processed chunks
- Unit test each retriever against the fixture corpus: assert correct return type, non-empty results, latency logging

**Exit criteria:** `scripts/build_indexes.py` runs clean, all four retrievers pass unit tests, each returns results in the shared schema.

---

### Phase 3 — Generation and Evaluation Loop
**Goal:** End-to-end pipeline from query → retrieval → generation → RAGAS scoring → logged to DB.

- Implement `generation/generator.py`: takes retrieved chunks + query, formats prompt, calls Gemini Flash, returns answer + token count
- Prompt template: system context explaining the domain, retrieved chunks as numbered passages, query, instruction to cite passages and not hallucinate
- Implement `evaluation/ragas_runner.py`: build RAGAS `EvaluationDataset` from (query, retrieved_context, generated_answer, ground_truth), run all four RAGAS metrics, return scores dict
- Implement `evaluation/operational.py`: wrap each retriever+generator call with a latency timer, extract token usage from LLM response
- Implement `evaluation/logger.py`: write one row per (query, strategy) to SQLite with all 6 metric values
- Write `scripts/run_eval.py`: iterate all 50 eval questions, run all 4 strategies per question, log everything to DB
- Run full eval suite, verify DB is populated correctly

**Exit criteria:** `scripts/run_eval.py` completes without errors, `results/evals.db` contains 200 rows (50 questions × 4 strategies), all 6 metrics populated.

---

### Phase 4 — Dashboard
**Goal:** Streamlit app that is live-demo-ready: interactive query runner + aggregate analytics + chunk inspector.

- Implement `dashboard/data_loader.py`: read from `evals.db`, expose DataFrames for aggregate and per-query views
- Implement `dashboard/components/query_runner.py`: text input + run button + per-strategy result cards
- Implement `dashboard/components/comparison.py`: side-by-side metric table with winner highlight
- Implement `dashboard/components/aggregate.py`: bar charts by metric, scatter plot quality vs cost, breakdown by query category
- Implement `dashboard/components/drilldown.py`: query selector + chunk diff view
- Wire up `dashboard/app.py` with sidebar navigation between views
- Test with live queries against all four strategies
- Test with historical data from `evals.db`

**Exit criteria:** `streamlit run dashboard/app.py` runs clean, all four views are functional, live query works end-to-end in under 5 seconds for Dense/BM25/Hybrid (Tree Index may take 10–30s, that is expected and should be labelled in the UI).

---

### Phase 5 — Findings and Documentation
**Goal:** The project produces a concrete, shareable engineering finding. Not just a working system — a result.

- Run `scripts/export_findings.py` to generate `results/summary.csv` and `results/findings.md`
- `findings.md` must contain:
  - Overall winner per metric across all 50 queries
  - Winner per query category (keyword / semantic / multi-hop / compound)
  - Cost vs quality trade-off analysis (quantified: "BM25 achieves X% of Dense quality at Y% of the token cost")
  - Recommendation framework: when to use which strategy
- Write `README.md` with: project summary, architecture diagram (ASCII), setup instructions, key findings (3–5 bullet points with numbers), demo screenshot or GIF
- Record a 2-minute walkthrough demo (screen recording): show a live query, walk through the comparison table, show the aggregate chart, call out the headline finding
- Tag `v1.0.0` release on GitHub

**Exit criteria:** `findings.md` exists with quantified results, `README.md` is complete, demo recording is done, GitHub repo is public.

---

## 11. Configuration

All runtime configuration lives in `.env`. No hardcoded API keys or paths.

```env
# LLM — Primary
GOOGLE_API_KEY=...
GENERATION_MODEL=gemini-1.5-flash

# LLM — Fallback
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile

# Models — Local (no API key needed)
EMBEDDING_MODEL=all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Retrieval
TOP_K=5                     # chunks to retrieve per strategy
CHUNK_SIZE=512              # tokens
CHUNK_OVERLAP=64            # tokens

# Paths
DATA_DIR=data/
RESULTS_DIR=results/
INDEX_DIR=data/indexes/
```

---

## 12. Key Design Decisions and Constraints

- **Same LLM for generation across all strategies.** The only variable being tested is retrieval. The generation model must be fixed to isolate the retrieval signal.
- **Same chunks as input for Dense, BM25, and Hybrid.** Tree Index uses the same chunks as leaf nodes but builds its own summary tree on top. Chunk quality affects all strategies equally.
- **RAGAS requires a ground truth answer for Context Recall.** The 50 eval questions must have hand-written ground truth answers — do not generate these with an LLM or the scores will be circular.
- **Tree Index is expensive.** Expect $0.01–$0.05 per query. Run Tree Index last in the eval loop and add a cost guard in `run_eval.py` that prints estimated cost before proceeding.
- **Do not use OpenAI embeddings for Dense in the default config.** Use `all-MiniLM-L6-v2` (local, free) to keep the project runnable without paid API access for the retrieval step.
- **Hybrid reranker is a cross-encoder, not a bi-encoder.** Cross-encoders score (query, chunk) pairs jointly. This is slower but more accurate than re-scoring embeddings. This distinction is interview-worthy.

---

## 13. What This Project Demonstrates

For interviews at ML/AI engineering roles, this project answers:

| Question | Evidence from this project |
|---|---|
| Can you build production RAG? | Four working retrieval pipelines on real regulatory documents |
| Do you understand LLM evaluation? | RAGAS integration, ground truth dataset, LLM-as-judge metrics |
| Do you think about cost and latency? | Operational metrics tracked per query per strategy |
| Can you make data-driven engineering decisions? | Quantified findings on when to use which strategy |
| Do you understand the limits of vector search? | BM25 outperforms Dense on keyword-heavy queries — demonstrated, not assumed |
| Can you build a demo? | Live Streamlit dashboard, 2-min walkthrough recording |

---

## 14. Out of Scope (do not build)

- Authentication or multi-user support
- Document upload UI (corpus is fixed, loaded via ingestion script)
- Fine-tuned embedding models
- Streaming LLM responses in the dashboard
- Deployment to cloud (run locally for the portfolio demo)
- Support for non-PDF document formats

---

## 15. Development Workflow — Multi-Agent Structure

This project is built using a structured multi-agent development loop across five agent roles. The same workflow runs on both Claude Code and Gemini CLI. Each agent has a single responsibility and reads only what it needs — the Codebase Graph (Section 16) is the shared memory that eliminates redundant file reads across agents.

### Agent Roles

#### Architect
- **Reads:** `SPEC.md`, current phase definition, `CODEBASE_GRAPH.md`
- **Produces:** A concrete task list for the current phase: which files to create, what each must export, what interfaces must match
- **Does not write code.** Only plans.
- **Trigger:** Start of each phase, or when scope changes mid-phase
- **Model guidance:** Use the most capable available model (Gemini 1.5 Pro or Claude Opus) — this is the high-stakes decision step

#### Coder
- **Reads:** Architect task list + `CODEBASE_GRAPH.md` + only the specific files relevant to the current task
- **Produces:** Working implementation, one file at a time
- **Does not review its own output.** Hands off to Reviewer after each file.
- **Model guidance:** Gemini 1.5 Flash or Claude Sonnet — high volume, medium stakes

#### Reviewer
- **Reads:** Changed file(s) + relevant section of `SPEC.md` + `CODEBASE_GRAPH.md`
- **Produces:** Inline review comments + updated `CODEBASE_GRAPH.md` status column
- **Checks:** Does the implementation match the spec? Are the interfaces correct? Are there obvious bugs? Is there dead code?
- **Does not fix code.** Returns to Coder with specific instructions if changes are needed.
- **Model guidance:** Claude Sonnet or Gemini 1.5 Flash

#### Security
- **Reads:** All files changed in the current phase
- **Produces:** Security report — hardcoded secrets, injection risks, API key exposure, unsafe subprocess calls
- **Runs once per phase**, not per file
- **Checks specific to this project:** No API keys in source, no `eval()` on user input, all LLM outputs treated as untrusted before DB write
- **Model guidance:** Any model — the checklist is mechanical

#### Documenter + GitHub Push
- **Reads:** `CODEBASE_GRAPH.md` + changed files + `SPEC.md` Section 13
- **Produces:** Updated `README.md` section for the completed phase, commit message, git push
- **Commit message format:** `feat(phase-N): <what was built>` — one line, present tense
- **Runs once per phase** after Security clears the changes

### Workflow Loop Per Phase

```
┌─────────────────────────────────────────────────────────┐
│  Phase N starts                                         │
│                                                         │
│  1. ARCHITECT reads SPEC phase N + CODEBASE_GRAPH.md   │
│     → outputs task list (files, interfaces, order)      │
│                                                         │
│  2. CODER picks task 1                                  │
│     reads CODEBASE_GRAPH.md + referenced files only     │
│     → writes file                                       │
│                                                         │
│  3. REVIEWER reads changed file + SPEC                  │
│     → approve or return to CODER with comments         │
│     → updates CODEBASE_GRAPH.md on approval            │
│                                                         │
│  repeat steps 2–3 for each task                         │
│                                                         │
│  4. SECURITY scans all phase N changes                  │
│     → approve or block (return to CODER)                │
│                                                         │
│  5. DOCUMENTER updates README + commits + pushes        │
│     → CODEBASE_GRAPH.md committed alongside code       │
│                                                         │
│  Phase N complete. Move to Phase N+1.                   │
└─────────────────────────────────────────────────────────┘
```

### Platform-Specific Notes

**Claude Code:**
- Architect, Reviewer, Security, and Documenter run as subagents via the `Agent` tool
- Coder runs inline (main context) — it needs read/write tool access
- Use worktree isolation (`isolation: "worktree"`) for the Coder on each phase so changes are isolated until Reviewer approves
- The `simplify` skill runs after Reviewer approval before Security — catches over-engineered code early

**Gemini CLI:**
- All agents are invoked as separate Gemini CLI sessions with scoped context
- Each agent session is given: its role prompt + `SPEC.md` + `CODEBASE_GRAPH.md` + only the files it needs
- Gemini CLI reads `GEMINI.md` from the project root — this file defines the active agent role and points to `SPEC.md`
- Switch agent roles by updating `GEMINI.md` to the role-specific prompt (see Section 17)

---

## 16. Codebase Graph — Token Management

The Codebase Graph is a lightweight markdown file (`CODEBASE_GRAPH.md`) maintained at the project root. It is the shared memory across all agents and sessions. Its purpose is to let any agent understand the full codebase structure without reading all source files.

**Rule:** Any agent that creates or modifies a file MUST update `CODEBASE_GRAPH.md` before handing off. Any agent that reads code MUST read `CODEBASE_GRAPH.md` first and load only the files listed as relevant to its task.

### Format

```markdown
# Codebase Graph — RAG Arena

Last updated: {date} | Phase: {current phase}

## File Registry

| File | Purpose | Exports | Status | Phase |
|------|---------|---------|--------|-------|
| src/ingestion/chunker.py | Sentence-boundary chunker | `chunk_document(text, chunk_size, overlap) -> List[Chunk]` | ✅ Reviewed | 1 |
| src/retrieval/base.py | Abstract Retriever base class | `Retriever(ABC)` with `retrieve(query, k) -> List[Chunk]` | ✅ Reviewed | 1 |
| src/retrieval/dense.py | FAISS + sentence-transformer retriever | `DenseRetriever(index_path)` | 🔄 In progress | 2 |

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

src/retrieval/dense.py        → src/retrieval/base.py, data/indexes/dense/
src/retrieval/bm25.py         → src/retrieval/base.py, data/indexes/bm25/
src/retrieval/tree_index.py   → src/retrieval/base.py, data/indexes/tree/
src/retrieval/hybrid.py       → src/retrieval/dense.py, src/retrieval/bm25.py
src/generation/generator.py   → (no internal deps)
src/evaluation/ragas_runner.py → src/generation/generator.py
src/evaluation/logger.py      → (no internal deps)
dashboard/app.py              → src/evaluation/logger.py (reads DB only)

## Review Status

| File | Reviewer verdict | Security verdict | Notes |
|------|-----------------|-----------------|-------|
| src/ingestion/chunker.py | ✅ Approved | ✅ Clean | — |
| src/retrieval/base.py    | ✅ Approved | ✅ Clean | — |
```

### Token Savings

Without the graph: Reviewer reads all source files = O(N files) tokens per review cycle.
With the graph: Reviewer reads `CODEBASE_GRAPH.md` + only the changed file = O(1) tokens per review cycle.

At 15 source files by Phase 3, this eliminates roughly 70–80% of redundant token usage across agent handoffs.

---

## 17. Platform Configuration Files

### CLAUDE.md (project root)

Place this at `rag-arena/CLAUDE.md`. Claude Code reads this automatically.

```markdown
# RAG Arena — Claude Code Instructions

## What this project is
A 4-way RAG retrieval benchmarking system. Full spec in SPEC.md.
Read SPEC.md before doing anything. Read CODEBASE_GRAPH.md before reading source files.

## Development workflow
Follow the multi-agent structure in SPEC.md Section 15.
Current phase and active tasks are in CODEBASE_GRAPH.md header.

## Rules
- Never hardcode API keys. All secrets via .env + python-dotenv.
- Never change interface contracts in CODEBASE_GRAPH.md without updating all dependent files.
- Every file you create or modify: update CODEBASE_GRAPH.md File Registry before stopping.
- Generation model must be identical across all 4 retrieval strategies in any single eval run.
- Do not generate ground truth answers with an LLM. data/eval/ground_truth.json is hand-written.

## Active agent role
Default: Coder.
If the user says "act as architect / reviewer / security / documenter" — switch to that role.
Role definitions are in SPEC.md Section 15.

## Stack
Python 3.11+, Gemini 1.5 Flash (primary), Groq/Llama 3.3 70B (fallback),
FAISS, rank-bm25, llama-index, RAGAS, Streamlit, SQLite.
```

### GEMINI.md (project root)

Place this at `rag-arena/GEMINI.md`. Gemini CLI reads this automatically.

```markdown
# RAG Arena — Gemini CLI Instructions

## What this project is
A 4-way RAG retrieval benchmarking system. Full spec in SPEC.md.
Read SPEC.md before doing anything. Read CODEBASE_GRAPH.md before reading source files.

## Development workflow
Follow the multi-agent structure in SPEC.md Section 15.
Current phase and active tasks are in CODEBASE_GRAPH.md header.

## Rules
- Never hardcode API keys. All secrets via .env + python-dotenv.
- Never change interface contracts in CODEBASE_GRAPH.md without updating all dependent files.
- Every file you create or modify: update CODEBASE_GRAPH.md File Registry before stopping.
- Generation model must be identical across all 4 retrieval strategies in any single eval run.
- Do not generate ground truth answers with an LLM. data/eval/ground_truth.json is hand-written.

## Active agent role
Check the line "ACTIVE ROLE: ..." at the top of this file.
Switch this line to change which agent role Gemini CLI is acting as.
Role definitions are in SPEC.md Section 15.

ACTIVE ROLE: Coder

## Stack
Python 3.11+, Gemini 1.5 Flash (primary), Groq/Llama 3.3 70B (fallback),
FAISS, rank-bm25, llama-index, RAGAS, Streamlit, SQLite.
```

**To switch Gemini CLI agent role:** Edit the `ACTIVE ROLE:` line in `GEMINI.md`. That single line change is all that's needed — no need to restructure the session.

### .claude/settings.json

```json
{
  "permissions": {
    "allow": [
      "Bash(python:*)",
      "Bash(pip:*)",
      "Bash(uv:*)",
      "Bash(pytest:*)",
      "Bash(streamlit:*)",
      "Bash(git:*)",
      "Bash(find:*)",
      "Bash(grep:*)",
      "Read(**)",
      "Write(src/**)",
      "Write(scripts/**)",
      "Write(tests/**)",
      "Write(dashboard/**)",
      "Write(CODEBASE_GRAPH.md)",
      "Write(README.md)"
    ]
  }
}
```

---

## 18. Quick Build Recommendations

### Use `uv` instead of `pip`
`uv` resolves and installs dependencies 10–100x faster than pip. Use `uv sync` instead of `pip install -r requirements.txt`. This matters during Phase 2 when you'll be adding heavy packages (FAISS, sentence-transformers, llama-index) and reinstalling repeatedly.

```bash
pip install uv
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

### Makefile for script shortcuts
All five CLI scripts have long names. A Makefile prevents typos and makes the project self-documenting for anyone cloning it.

```makefile
ingest:
	python scripts/ingest.py

build-indexes:
	python scripts/build_indexes.py

eval:
	python scripts/run_eval.py

dashboard:
	streamlit run dashboard/app.py

test:
	pytest tests/ -v

findings:
	python scripts/export_findings.py
```

### Pre-commit hooks (black + ruff)
Reviewer agent shouldn't spend tokens on style. Set up pre-commit once so formatting is automatic.

```bash
uv pip install pre-commit black ruff
pre-commit install
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.0.0
    hooks: [{ id: black }]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks: [{ id: ruff, args: [--fix] }]
```

### GitHub Actions from Phase 1
Set up CI on day one. Every push to `main` runs `pytest tests/`. This is cheap and catches regressions before the Reviewer has to.

`.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install uv && uv pip install -r requirements.txt
      - run: pytest tests/ -v
```

### Branch per phase
One branch per phase: `phase-1-foundation`, `phase-2-retrieval`, etc. PR into `main` after Security and Documenter sign off. This gives you a clean git history that tells the build story and is impressive to show interviewers.
