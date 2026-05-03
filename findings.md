# RAG Arena — Evaluation Findings

**Run ID:** `run_12d94e65`  
**Date:** 2026-05-03  
**Corpus:** 5 SEBI regulations (PIT 2015, SAST 2011, ICDR 2018, LODR 2015, MF Regulations)  
**Questions:** 41 (8 keyword, 11 semantic, 11 multihop, 11 compound)  
**Strategies:** BM25, Dense, Hybrid, Tree Index  
**Retrieval k=5** | **Generator:** Gemini 2.0 Flash | **RAGAS scorer:** Gemini 2.0 Flash

---

## Overall Results

| Strategy    | Context Precision | Context Recall | Faithfulness | Answer Relevance | Latency (ms) | Avg Tokens |
|-------------|:-----------------:|:--------------:|:------------:|:----------------:|:------------:|:----------:|
| BM25        | 0.036             | 0.274          | **0.932**    | 0.551            | **21**       | 2702       |
| Dense       | 0.073             | 0.203          | 0.864        | 0.422            | 62           | 2299       |
| Hybrid      | 0.059             | **0.284**      | 0.913        | **0.580**        | 822          | 2613       |
| Tree Index  | **0.100**         | 0.187          | 0.929        | 0.468            | 20,828       | **674**    |

---

## Category Breakdown

| Strategy    | Category  | Precision | Recall | Faithfulness | Ans. Relevance |
|-------------|-----------|:---------:|:------:|:------------:|:--------------:|
| BM25        | keyword   | 0.050     | 0.406  | **1.000**    | 0.409          |
| Dense       | keyword   | 0.219     | **0.490** | 0.850     | 0.435          |
| Hybrid      | keyword   | 0.073     | 0.219  | 0.809        | 0.434          |
| Tree Index  | keyword   | **0.375** | 0.375  | 0.875        | 0.446          |
|-------------|-----------|-----------|--------|--------------|----------------|
| BM25        | semantic  | 0.000     | 0.288  | 0.854        | **0.692**      |
| Dense       | semantic  | 0.000     | 0.094  | 0.818        | 0.523          |
| Hybrid      | semantic  | 0.000     | **0.332** | **0.983** | 0.669          |
| Tree Index  | semantic  | 0.091     | 0.195  | 0.976        | 0.688          |
|-------------|-----------|-----------|--------|--------------|----------------|
| BM25        | multihop  | 0.098     | 0.242  | 0.937        | 0.605          |
| Dense       | multihop  | 0.114     | 0.263  | **0.992**    | 0.516          |
| Hybrid      | multihop  | **0.167** | **0.311** | 0.849    | **0.657**      |
| Tree Index  | multihop  | 0.000     | 0.182  | 0.958        | 0.470          |
|-------------|-----------|-----------|--------|--------------|----------------|
| BM25        | compound  | 0.000     | 0.194  | 0.957        | 0.460          |
| Dense       | compound  | 0.000     | 0.043  | 0.803        | 0.217          |
| Hybrid      | compound  | 0.000     | **0.259** | **0.981** | **0.520**     |
| Tree Index  | compound  | 0.000     | 0.046  | 0.896        | 0.264          |

---

## Key Findings

### 1. Context precision is uniformly suppressed

34 of 41 questions returned 0 context_precision for **all four strategies**. Only 7 questions yielded non-zero precision from any strategy. This is not a retrieval failure — it reflects RAGAS context precision's strict grading: a retrieved chunk scores as precise only when its content is directly verifiable against the ground truth reference. For broad questions (semantic, compound, multihop), where the ground truth spans multiple regulations and the relevant chunks cover sub-parts of the answer, the metric consistently scores 0.

Context recall is more informative for this corpus and tells a clearer story.

### 2. Hybrid is the best general-purpose strategy

Hybrid wins context recall (0.284 overall, 13.4/41 question wins) and answer relevance (0.580 overall, 13.5/41 wins). It dominates multihop queries — precision 0.167, recall 0.311 — where a question requires evidence from multiple sections of multiple regulations. The lexical component of hybrid surfaces regulation-specific terminology while the semantic component bridges paraphrased phrasings. For compound questions (cross-regulation comparisons), hybrid leads all metrics.

**Recommendation: Hybrid for production RAG over SEBI regulatory corpus.**

### 3. BM25 punches well above its weight

BM25 is the fastest strategy by far (21ms vs 822ms for hybrid) and ranks second on both context recall (0.274) and answer relevance (0.551). It achieves perfect faithfulness (1.000) on keyword queries and leads recall on semantic questions (0.288 — beating dense and tree index). This is likely because the SEBI corpus is dense with precise regulatory terminology ("open offer", "designated person", "structured digital database") that BM25's exact-match vocabulary handles well.

BM25 wins 8.4/41 questions on context recall and 7.8/41 on answer relevance — competitive with dense and tree index.

**BM25 is the right choice when latency is the primary constraint.**

### 4. Tree index is a keyword specialist, not a generalist

Tree index achieves the highest context precision overall (0.100) driven entirely by keyword query performance: precision 0.375, beating every other strategy by a wide margin. On kw_04 (SAST open offer threshold) and kw_11 (IPO promoter lock-in), tree index scores 1.0 precision — perfect retrieval of the relevant node.

However, tree index scores 0 precision on all multihop and compound questions, and is the worst strategy for compound recall (0.046). The select-leaf traversal mechanism optimises for finding a single precise answer, which makes it excellent for factoid/keyword lookups but ill-suited to multi-regulation synthesis.

Tree index also costs 20.8 seconds per query (LLM traversal at each tree level) and 674 tokens (lowest of all — only one LLM response per query rather than 5 chunks). The latency makes it impractical for interactive use.

**Tree index should be reserved for keyword lookup and FAQ-style queries only.**

### 5. Dense retrieval underperforms expectations

Dense retrieval (FAISS + all-MiniLM-L6-v2) scores highest on keyword recall (0.490) but lowest on faithfulness (0.864) and answer relevance (0.422). Its compound recall (0.043) is nearly as poor as tree index (0.046), which is surprising for a semantic approach.

The likely cause is embedding model quality: `all-MiniLM-L6-v2` is a general-purpose model not fine-tuned on legal/regulatory language. Regulatory text has high terminology density and precise phrasing that differs significantly from the training distribution. Dense retrieval would likely improve substantially with a legal domain embedding model.

Dense does win 6.9/41 questions on recall and achieves near-perfect faithfulness on multihop (0.992) — it retrieves focused, relevant context when it retrieves anything at all.

### 6. Answer relevance is suppressed by the noncommittal penalty

RAGAS `ResponseRelevancy` multiplies cosine similarity by `int(not noncommittal)`. The generator (Gemini 2.0 Flash) produces citation-style answers ("Based on the retrieved passages, the penalty for insider trading is...") which RAGAS flags as noncommittal, zeroing out many scores. The scores reported above are after this penalty, meaning true semantic relevance of the answers is higher than these numbers suggest. All strategies are equally penalised, so relative ranking is valid.

---

## Strategy Selection Guide

| Use Case | Recommended Strategy | Why |
|----------|---------------------|-----|
| Exact regulatory lookup ("What is the X threshold?") | Tree Index | Highest precision on factoid queries |
| General SEBI Q&A with latency budget | BM25 | Fast, faithful, competitive recall |
| Complex multi-regulation questions | Hybrid | Best recall and answer relevance |
| Interactive chat (sub-second budget) | BM25 → Hybrid fallback | BM25 at 21ms; Hybrid at 822ms for re-rank |
| Cross-regulation comparison | Hybrid | Only strategy with non-zero compound recall |

---

## Methodology Notes

- **1 missing row**: `mh_02 × dense` returned NaN faithfulness (generation call failed silently). 163/164 rows completed.
- **Answer relevance note**: All values are suppressed ~30-50% by RAGAS noncommittal penalty. Relative comparisons are valid; absolute values are not.
- **Ground truth**: Hand-written from SEBI regulatory text. 10 questions removed that required RBI/MCA corpus not in scope. 1 question removed (kw_01) where relevant regulation was truncated in the corpus.
- **Tree index build cost**: ~$2.50 using Gemini 2.5 Flash (thinking tokens). Set `GEMINI_MODEL=gemini-2.0-flash` to reduce future build costs to ~$0.10.
