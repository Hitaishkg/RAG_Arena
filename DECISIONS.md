# RAG Arena — Decision Log

> **This file is write-only reference for the project owner.**
> It is not read by Claude or Gemini during task execution.
> It documents every architectural, operational, and strategic decision made
> during the build — including the reasoning, the alternatives rejected, and
> decisions that are locked for the future.

---

## Table of Contents

1. [Project Philosophy](#1-project-philosophy)
2. [Multi-Agent Architecture](#2-multi-agent-architecture)
3. [Token Management Strategy](#3-token-management-strategy)
4. [Cost Estimates](#4-cost-estimates)
5. [Vector Database Choice](#5-vector-database-choice)
6. [Chunking Strategy](#6-chunking-strategy)
7. [Study Design — No Prejudice Principle](#7-study-design--no-prejudice-principle)
8. [LLM Stack Decisions](#8-llm-stack-decisions)
9. [Storage and Infrastructure Decisions](#9-storage-and-infrastructure-decisions)
10. [Repository and Workflow Decisions](#10-repository-and-workflow-decisions)
11. [Future Decisions (locked in advance)](#11-future-decisions-locked-in-advance)

---

## 1. Project Philosophy

**Decision:** This project is a scientific benchmark, not a product showcase.

The goal is to answer: *"Which retrieval strategy is best for RBI/SEBI regulatory documents, and is the quality premium of expensive strategies worth the cost?"*

This means:
- No strategy is assumed to win
- Parameters are chosen for quality, not to flatter any particular strategy
- If Dense/vector search performs badly on this corpus, that is the result and it gets reported
- The study should be reproducible — same chunks, same LLM, same eval dataset, same judge model

**Why this matters:** Most RAG comparisons online are written by people who already chose vector search and are retroactively justifying it. This project does the opposite — measure first, conclude after.

---

## 2. Multi-Agent Architecture

### Roles (decided in conversation, locked)

| Agent | Role | Owns |
|-------|------|------|
| Claude | Architect + Orchestrator + Reviewer + Security | Design, task specification, review, commit/push |
| Gemini | Implementer | Writing code exactly as specified |

**Why Claude as Architect:** Core decisions — interfaces, versions, quality bar, review — require consistent reasoning across the whole project. Having one agent own architecture prevents design drift. Gemini handles volume work (file writing) while Claude maintains coherence.

**Why Gemini as Implementer:** Gemini 1.5 Flash is fast and cheap for code generation volume. It runs headlessly without needing an interactive session. It can be triggered, complete a focused task, and exit — clean and stateless per invocation.

### Trigger mechanism (confirmed working)

```bash
/home/hitaish/.npm-global/bin/gemini -p "$(cat .agent/TASK.md)" --approval-mode=yolo
```

Flags tested and confirmed:
- `-y` and `--approval-mode` cannot be combined — use `--approval-mode=yolo` alone
- Output noise to strip: "YOLO mode is enabled" (×2) + "Ripgrep is not available. Falling back to GrepTool."
- Actual response follows the noise lines

### Handoff protocol

```
Claude writes → .agent/TASK.md      (task brief for Gemini)
Gemini writes → .agent/GEMINI_DONE.md  (completion summary for Claude)
```

Both files are gitignored (transient working state — no value in git history).

### Communication flow per task

```
Claude: write TASK.md → trigger Gemini → wait for exit
Gemini: read TASK.md + CODEBASE_GRAPH.md + named files → implement → update CODEBASE_GRAPH.md → write GEMINI_DONE.md
Claude: read GEMINI_DONE.md → review changed files → PASS or re-trigger with fix
```

### What Gemini gets per call (hard limit)

- `.agent/TASK.md` — the task brief
- `CODEBASE_GRAPH.md` — current codebase state
- Only the specific source files named in TASK.md

Gemini never gets:
- The full spec (too large, CODEBASE_GRAPH.md replaces it)
- Files not named in the task brief
- Architectural rationale beyond what's needed to implement

### Swarm usage

**Claude's Agent tool:** Reviewer and Security subagents run in parallel when multiple files are ready. Explore subagent handles heavy codebase searches without polluting main context.

**Gemini parallel invocations:** For independent files in the same phase (e.g., `dense.py` and `bm25.py` have no dependencies between them), two Gemini calls can be triggered in sequence with separate TASK files. True parallelism not used — sequential is safer for file conflict avoidance.

---

## 3. Token Management Strategy

### The core failure mode we are preventing

```
Task starts → context fills → auto-compression → critical interface detail is lost
→ Gemini output is inconsistent with rest of codebase → silent bug → surfaces in Phase 3
```

### Prevention: state externalization

`CODEBASE_GRAPH.md` holds project state. Not conversation history. This means:
- Any fresh Claude session can read one file and resume
- Context compression cannot lose interface contracts or dependency info
- After every completed task, CODEBASE_GRAPH.md is updated before moving on

### Claude context hygiene rules

1. Use Explore subagent for codebase searches — keeps main context clean
2. Read files with line ranges when only a section is needed
3. Never hold multiple full file contents in context simultaneously
4. Summarize Gemini output inline after review — don't accumulate raw tool outputs
5. Before starting a new phase: write CODEBASE_GRAPH.md checkpoint first

### Gemini invocation rules

1. One task = one file = one Gemini call. Never a whole phase in one shot.
2. Estimate token load before writing TASK.md: TASK.md (~500) + CODEBASE_GRAPH.md (~2000) + named files. Gemini Flash has 1M context — individual file tasks are safe.
3. GEMINI_DONE.md is mandatory. Missing file = partial/failed run. New TASK.md targets only remaining work.
4. If a task is too large to fit one invocation cleanly, it gets split before starting.

### Checkpointing in code (future decision, locked)

- `tree_index.py` build: checkpoint after each tree level to disk. Restart resumes from last completed level.
- `run_eval.py`: write SQLite row immediately per (question, strategy) pair. Crash at question 35 = 35 rows safe, restart at question 36.

---

## 4. Cost Estimates

### API cost per component

All retrieval embedding and reranking is **local/free** (`all-MiniLM-L6-v2`, `cross-encoder/ms-marco-MiniLM-L-6-v2`). API cost only comes from LLM calls (Gemini Flash).

**Gemini 1.5 Flash pricing (as of project start):**
- Input: ~$0.075 per 1M tokens
- Output: ~$0.30 per 1M tokens

### Phase-by-phase cost estimate

**Phase 1 — Ingestion/Foundation:** ~$0.00
- No LLM calls. Chunking is local. Embeddings are local.

**Phase 2 — Tree Index build (most expensive single operation):**
- Corpus: ~3000 chunks (500–1500 pages, 512 tokens each)
- Build summaries: ~3000 leaf→L1 calls + ~300 L1→L2 calls + ~30 L2→root = ~3330 calls
- Avg tokens per call: 600 input + 150 output = 750 tokens
- Total: 3330 × 750 = ~2.5M tokens
- Cost: ~$0.19 input + ~$0.15 output = **~$0.35 to build the tree**

**Phase 3 — Full eval run (50 questions × 4 strategies):**

| Operation | Calls | Avg tokens | Total tokens | Cost |
|-----------|-------|-----------|--------------|------|
| Generation (200 calls) | 200 | 3000 input + 300 output | 600K in + 60K out | ~$0.06 |
| RAGAS judge (4 metrics × 200) | 800 | 3500 input + 100 output | 2.8M in + 80K out | ~$0.23 |
| Tree traversal (50 × 3 hops) | 150 | 1200 input + 100 output | 180K in + 15K out | ~$0.015 |
| **Full eval run total** | | | | **~$0.30** |

**Total project API cost estimate: $1.00–$2.00**

Includes: one tree build + 2–3 full eval runs during development + buffer for re-runs.

If eval is run many times during debugging: $5–$10 maximum.

**Groq fallback cost:** Free tier. Used only when Gemini hits rate limits. No additional cost.

**Claude Code sessions:** Billed separately to Anthropic account. Not included above.

### Cost guard rule (locked)

Before running Tree Index on the full eval set, `run_eval.py` will:
1. Calculate estimated cost based on corpus size
2. Print: "Estimated cost for Tree Index eval: $X.XX. Proceed? (y/n)"
3. Require explicit confirmation before proceeding

---

## 5. Vector Database Choice

**Decision: FAISS (faiss-cpu) with IndexFlatIP**

### What was considered

| Option | Type | Cost | Infrastructure | Decision |
|--------|------|------|----------------|----------|
| FAISS | Local library | Free | None | **Chosen** |
| Chroma | Local server | Free | Needs server process | Rejected |
| Qdrant | Local/cloud | Free/paid | Needs Docker or cloud | Rejected |
| Pinecone | Cloud | Paid | External API | Rejected |
| Weaviate | Local/cloud | Free/paid | Needs Docker | Rejected |

### Why FAISS

1. **Zero infrastructure.** No server to start, no Docker, no API key. The index is a single file on disk (`data/indexes/dense/index.faiss`). This matters because the project runs fully locally — no cloud services.

2. **Exact nearest-neighbor search.** `IndexFlatIP` (inner product) with L2-normalized vectors = exact cosine similarity search. No approximation. For a benchmark where we're measuring retrieval quality, approximate search introduces noise. We want to test the embedding model and chunking strategy, not FAISS's approximation algorithm.

3. **Scale is trivial.** 3000 chunks × 384 dimensions (all-MiniLM-L6-v2 output size) = a 4.6MB index. Flat search over 3000 vectors takes ~1–2ms on CPU. No need for HNSW, IVF, or any approximate method.

4. **Serializable to disk.** `faiss.write_index()` / `faiss.read_index()` — the index builds once and reloads in milliseconds. No rebuild needed per session.

5. **Consistent with the spec.** The spec explicitly states: "Do not use OpenAI embeddings for Dense in the default config. Use all-MiniLM-L6-v2 (local, free)." FAISS is the natural pairing for local embeddings.

### Index type decision: IndexFlatIP (not IndexFlatL2)

- all-MiniLM-L6-v2 embeddings should be L2-normalized before indexing
- For L2-normalized vectors: inner product = cosine similarity
- `IndexFlatIP` with normalized vectors is cosine similarity search
- Cosine similarity is the standard for sentence-transformer models
- Alternative `IndexFlatL2` (Euclidean distance) gives different rankings and is the wrong metric for this embedding model

### What FAISS does NOT give us

- No metadata filtering (filter by doc_id, section, etc.) at search time
- We handle this in post-processing: retrieve top-k, then filter by metadata if needed
- At 3000 chunks this is fast enough to not matter

---

## 6. Chunking Strategy

### Parameters (from spec, validated by exploration notebook before Phase 2)

- Chunk size: 512 tokens
- Overlap: 64 tokens (~12.5%)
- Boundary: sentence-aware — never cut mid-sentence
- Metadata per chunk: `{doc_id, page_number, section_header, char_start, char_end}`

### Why these parameters are not tuned to favor any strategy

The same chunks feed Dense, BM25, and Tree Index. Tuning chunk size to make Dense look better would also affect BM25 and Tree Index. The parameters are chosen for chunk quality (complete thoughts, no broken sentences, section context preserved) — not for any strategy's benefit.

### Mandatory pre-Phase 2 verification checklist

Run in `notebooks/exploration.ipynb` before building any index:

1. Length distribution plot — bell curve around 400–512 tokens expected. Spikes below 100 = garbage extraction (headers, footers). Spikes above 600 = hard cap not working.
2. Sample 50 random chunks — verify first and last word are sentence-terminal.
3. Overlap check — last 64 tokens of chunk N == first 64 tokens of chunk N+1.
4. Section header coverage — `section` metadata populated in ≥80% of chunks.
5. Manual read — 20 chunks from different documents. Does each make standalone sense?

If any check fails, fix the chunker before building indexes. No shortcuts.

### Why sentence-boundary matters more for Dense than BM25

A chunk that cuts mid-clause produces a broken embedding — the sentence-transformer encodes an incomplete thought. BM25 doesn't care: it just indexes the tokens present, partial or not. This means bad chunking biases results against Dense. Since we are running a fair benchmark, chunking must be as clean as possible so we're measuring retrieval strategy quality, not chunker quality.

---

## 7. Study Design — No Prejudice Principle

**Decision (owner-stated, locked):** This is a scientific study. No strategy is assumed to win.

### Expected outcome (hypothesis, not assumption)

RBI/SEBI documents are keyword-heavy regulatory text. The natural language is precise and consistent — documents use the exact same terminology they expect in queries. This means:

- **BM25 is likely strong** on keyword queries ("minimum capital requirement for payment aggregator") because the exact phrase appears in the document
- **Dense is likely weak** on those same queries because it was designed for semantic similarity, not exact term matching — and it has more overhead for no gain
- **Dense may recover** on paraphrased or conceptual queries
- **Tree Index is the wildcard** — structure-navigation is its edge, but RBI/SEBI docs may or may not have deep enough hierarchy to justify the cost
- **Hybrid should be most robust** but at the highest cost

These are hypotheses. The eval dataset will confirm or refute each one. If Dense beats BM25 on keyword queries, we report it and understand why.

### The eval dataset split (intentional)

50 questions, 12–13 per category:
- Keyword queries: exact phrase from document — BM25 expected to lead
- Semantic queries: paraphrased question — Dense expected to lead
- Multi-hop/hierarchical: answer spans sections — Tree Index expected to lead
- Compound queries: multi-part, broad recall needed — Hybrid expected to lead

The split is designed so every strategy has a query type where it *should* win. This makes the comparison meaningful rather than one strategy dominating. If a strategy loses even on its "home turf," that is a real finding.

---

## 8. LLM Stack Decisions

### Primary: Gemini 1.5 Flash

**Why:** Free API tier with generous limits. Fast inference. Available via `google-generativeai`. Cheap enough to use for Tree Index node summarization (high call volume).

### Fallback: Groq / Llama 3.3 70B

**Why:** Free tier, very fast inference, completely independent of Google's infrastructure. Rate limit safety net only — same prompt, same output format, just a different endpoint.

**Trigger:** Gemini call fails or hits rate limit → retry once → fall back to Groq. Implemented in `generation/generator.py`.

### Critical constraint: same LLM for generation across all 4 strategies

The only variable being tested is retrieval. Generation must be identical. If Dense uses Gemini Flash and BM25 uses Llama, the answer quality difference could come from the LLM, not the retrieval strategy. This constraint is enforced in code — `run_eval.py` verifies that the same model string is used for all strategies before starting.

### Embeddings: all-MiniLM-L6-v2 (local, sentence-transformers)

**Why:** Zero API cost. Runs on CPU. 384-dimension output (small index, fast search). Standard benchmark model. No external dependency at retrieval time.

### Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2 (local, sentence-transformers)

**Why:** Cross-encoder scores (query, chunk) pairs jointly — more accurate than re-scoring embeddings because it sees the interaction between query and chunk. This is architecturally correct for a hybrid reranker. Zero API cost. Runs on CPU.

**Interview note:** This is a cross-encoder, not a bi-encoder. The distinction matters — bi-encoders encode query and chunk independently and compare embeddings. Cross-encoders encode the pair together and output a relevance score. Cross-encoders are slower but more accurate. This is the right choice for a reranker (not for initial retrieval, where speed matters).

---

## 9. Storage and Infrastructure Decisions

### SQLite (not PostgreSQL, not a cloud DB)

**Why:** Zero infrastructure. Single file. Portable. Queryable with standard pandas. The eval results (200 rows) are trivially small — there is no performance reason to use anything heavier. The project must run fully locally with no external services.

### FAISS index stored to disk (not in memory only)

**Why:** Build once, load in milliseconds. No rebuild per session. Index files live in `data/indexes/` (gitignored — too large for git and reproducible from source documents).

### No streaming, no cloud deployment (out of scope, locked)

Streaming LLM responses in the dashboard: out of scope. Cloud deployment: out of scope for the portfolio demo phase. The demo runs locally. When the project goes live (post-Phase 5), deployment decisions will be made then.

---

## 10. Repository and Workflow Decisions

### Branch strategy: one branch per phase

`phase-1-foundation`, `phase-2-retrieval`, `phase-3-eval`, `phase-4-dashboard`, `phase-5-findings`

PR into `main` after Security and Documenter sign off. Git history tells the build story.

### Commit message format (locked)

`feat(phase-N): <what was built>` — one line, present tense.

### Repository: private now, public at v1.0.0

Private during development. Flipped to public when Phase 5 is complete, demo is recorded, findings are written. GitHub: `github.com/Hitaishkg/RAG_Arena`.

### Package manager: uv (not pip)

All installs via `uv pip install` or `uv sync`. Never `pip install` directly. Reason: 10–100x faster resolution and installation. Matters during Phase 2 when heavy packages (FAISS, sentence-transformers, llama-index) are added repeatedly.

### Pre-commit hooks: black + ruff

Formatting and linting is automatic. Reviewer agent does not spend tokens on style. Set up once in Phase 1, runs on every commit.

### CI: GitHub Actions from Phase 1

Every push to `main` runs `pytest tests/ -v`. Catches regressions before Reviewer has to find them.

### Ground truth: hand-written only (locked forever)

`data/eval/ground_truth.json` contains the 50 expected answers. These are written by the project owner from source documents. Never generated by an LLM. Reason: if ground truth is LLM-generated, Context Recall scores become circular — the judge and the answer generator share the same model biases. This would make the eval meaningless.

---

## 11. Future Decisions (locked in advance)

These decisions are made now to prevent debate or drift later.

**FAISS index type stays as IndexFlatIP.** Do not switch to HNSW or IVF for speed. At 3000 chunks, exact search is fast enough and approximate search would introduce measurement noise.

**Embedding model stays as all-MiniLM-L6-v2.** Do not upgrade to a larger model mid-project. This would require rebuilding the FAISS index and re-running the full eval, breaking comparability with earlier runs.

**Chunk parameters (512/64) are finalized after the Phase 1 exploration notebook.** They do not change after Phase 2 indexes are built. If chunk quality is poor, fix the chunker in Phase 1, re-run ingestion, then build indexes. Never change chunking after indexes exist.

**The 50 eval questions are finalized before Phase 3 starts.** Do not add or remove questions after eval runs begin. Changing the eval set invalidates all previous scores.

**Tree Index runs last in every eval loop.** Cost guard in `run_eval.py` prints estimated cost and requires explicit confirmation before Tree Index queries begin. This applies every run, no exceptions.

**Groq fallback is transparent to the eval.** If a Gemini call falls back to Groq, that fact is logged in the eval row. Results from fallback calls are flagged in the analysis. If the fallback rate is high, the run is considered unreliable and should be re-run.

**No fine-tuning.** Embedding model and reranker are used off-the-shelf. Fine-tuning on the RBI/SEBI corpus would make the Dense results incomparable to a real-world deployment where fine-tuning isn't done.

---

*Last updated: 2026-05-01*
*Next update: after Phase 1 chunk quality verification*
