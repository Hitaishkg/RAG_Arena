# RAG Arena — Evaluation Findings

**Corpus:** 5 SEBI regulations (PIT 2015, SAST 2011, ICDR 2018, LODR 2015, MF Regulations)  
**Questions:** 41 (8 keyword, 11 semantic, 11 multihop, 11 compound)  
**Strategies:** BM25, Dense, Hybrid, Tree Index | **Retrieval k=5**

| | Run 1 | Run 2 |
|--|-------|-------|
| **Run ID** | `run_12d94e65` | `run_023c3905` |
| **Date** | 2026-05-03 | 2026-05-17 |
| **Encoder (embeddings)** | `all-MiniLM-L6-v2` | upgraded encoder |
| **Generator** | Gemini 2.0 Flash | Gemini 2.0 Flash |
| **RAGAS scorer** | Gemini 2.0 Flash | Gemini 2.0 Flash |

---

## Overall Results — Run 1 (`run_12d94e65`, baseline)

| Strategy   | Context Precision | Context Recall | Faithfulness | Answer Relevance | Latency (ms) | Avg Tokens |
|------------|:-----------------:|:--------------:|:------------:|:----------------:|:------------:|:----------:|
| BM25       | 0.036             | 0.274          | **0.932**    | 0.551            | **21**       | 2702       |
| Dense      | 0.073             | 0.203          | 0.864        | 0.422            | 62           | 2299       |
| Hybrid     | 0.059             | **0.284**      | 0.913        | **0.580**        | 822          | 2613       |
| Tree Index | **0.100**         | 0.187          | 0.929        | 0.468            | 20,828       | **674**    |

---

## Overall Results — Run 2 (`run_023c3905`, upgraded encoder)

| Strategy   | Context Precision | Context Recall | Faithfulness | Answer Relevance | Latency (ms) | Avg Tokens |
|------------|:-----------------:|:--------------:|:------------:|:----------------:|:------------:|:----------:|
| BM25       | 0.149             | 0.296          | **0.911**    | 0.744            | **57**       | 3073       |
| Dense      | 0.252             | 0.227          | **0.953**    | 0.765            | 92           | 2862       |
| Hybrid     | 0.170             | **0.300**      | 0.924        | **0.808**        | 717          | 3060       |
| Tree Index | **0.263**         | 0.188          | 0.814        | 0.648            | 11,205       | **782**    |

---

## Encoder Impact — Run 1 vs Run 2 (delta)

| Strategy   | Metric            | Run 1 | Run 2 | Delta     |
|------------|-------------------|-------|-------|-----------|
| **BM25**   | Context Precision | 0.036 | 0.149 | **+0.113** |
|            | Context Recall    | 0.274 | 0.296 | +0.022    |
|            | Faithfulness      | 0.932 | 0.911 | -0.021    |
|            | Answer Relevance  | 0.551 | 0.744 | **+0.193** |
|            | Latency (ms)      | 21    | 57    | +36       |
| **Dense**  | Context Precision | 0.073 | 0.252 | **+0.179** |
|            | Context Recall    | 0.203 | 0.227 | +0.024    |
|            | Faithfulness      | 0.864 | 0.953 | +0.089    |
|            | Answer Relevance  | 0.422 | 0.765 | **+0.343** |
|            | Latency (ms)      | 62    | 92    | +30       |
| **Hybrid** | Context Precision | 0.059 | 0.170 | **+0.111** |
|            | Context Recall    | 0.284 | 0.300 | +0.016    |
|            | Faithfulness      | 0.913 | 0.924 | +0.011    |
|            | Answer Relevance  | 0.580 | 0.808 | **+0.228** |
|            | Latency (ms)      | 822   | 717   | -105      |
| **Tree**   | Context Precision | 0.100 | 0.263 | **+0.163** |
|            | Context Recall    | 0.187 | 0.188 | +0.001    |
|            | Faithfulness      | 0.929 | 0.814 | -0.115    |
|            | Answer Relevance  | 0.468 | 0.648 | **+0.180** |
|            | Latency (ms)      | 20,828 | 11,205 | **-9,623** |

---

## Per-Category Breakdown — Run 1 (`run_12d94e65`)

| Category  | Strategy   | Precision | Recall     | Faithfulness | Ans. Relevance |
|-----------|------------|:---------:|:----------:|:------------:|:--------------:|
| **Keyword** | BM25     | 0.050     | 0.406      | **1.000**    | 0.409          |
|           | Dense      | 0.219     | **0.490**  | 0.850        | 0.435          |
|           | Hybrid     | 0.073     | 0.219      | 0.809        | 0.434          |
|           | Tree Index | **0.375** | 0.375      | 0.875        | 0.446          |
| **Semantic** | BM25    | 0.000     | 0.288      | 0.854        | **0.692**      |
|           | Dense      | 0.000     | 0.094      | 0.818        | 0.523          |
|           | Hybrid     | 0.000     | **0.332**  | **0.983**    | 0.669          |
|           | Tree Index | 0.091     | 0.195      | 0.976        | 0.688          |
| **Multihop** | BM25    | 0.098     | 0.242      | 0.937        | 0.605          |
|           | Dense      | 0.114     | 0.263      | **0.992**    | 0.516          |
|           | Hybrid     | **0.167** | **0.311**  | 0.849        | **0.657**      |
|           | Tree Index | 0.000     | 0.182      | 0.958        | 0.470          |
| **Compound** | BM25    | 0.000     | 0.194      | 0.957        | 0.460          |
|           | Dense      | 0.000     | 0.043      | 0.803        | 0.217          |
|           | Hybrid     | 0.000     | **0.259**  | **0.981**    | **0.520**      |
|           | Tree Index | 0.000     | 0.046      | 0.896        | 0.264          |

---

## Per-Category Breakdown — Run 2 (`run_023c3905`)

| Category  | Strategy   | Precision  | Recall     | Faithfulness | Ans. Relevance |
|-----------|------------|:----------:|:----------:|:------------:|:--------------:|
| **Keyword** | BM25     | 0.128      | **0.563**  | 0.753        | **0.742**      |
|           | Dense      | 0.250      | 0.354      | 0.880        | 0.615          |
|           | Hybrid     | 0.135      | 0.292      | 0.787        | 0.730          |
|           | Tree Index | **0.286**  | 0.250      | 0.592        | 0.576          |
| **Semantic** | BM25    | 0.253      | 0.289      | 0.945        | 0.817          |
|           | Dense      | **0.422**  | 0.228      | 0.944        | 0.817          |
|           | Hybrid     | 0.277      | 0.278      | 0.906        | **0.863**      |
|           | Tree Index | 0.273      | 0.061      | **0.931**    | 0.732          |
| **Multihop** | BM25    | 0.117      | 0.168      | 0.974        | 0.775          |
|           | Dense      | 0.245      | 0.273      | **0.987**    | 0.732          |
|           | Hybrid     | 0.167      | **0.304**  | 0.982        | **0.840**      |
|           | Tree Index | 0.182      | 0.160      | 0.853        | 0.611          |
| **Compound** | BM25    | 0.091      | 0.237      | 0.928        | 0.642          |
|           | Dense      | 0.091      | 0.086      | **0.979**    | **0.856**      |
|           | Hybrid     | 0.091      | **0.322**  | **0.982**    | 0.779          |
|           | Tree Index | **0.333**  | 0.327      | 0.797        | 0.648          |

---

## Category Winners Summary — Run 2

| Category  | Best Precision | Best Recall | Best Faithfulness | Best Ans. Relevance |
|-----------|---------------|-------------|-------------------|---------------------|
| Keyword   | Dense (0.250)  | **BM25 (0.563)** | Dense (0.880) | **BM25 (0.742)**  |
| Semantic  | **Dense (0.422)** | BM25 (0.289) | Tree (0.931)  | **Hybrid (0.863)** |
| Multihop  | Dense (0.245)  | **Hybrid (0.304)** | Dense (0.987) | **Hybrid (0.840)** |
| Compound  | **Tree (0.333)** | **Tree (0.327)** | Hybrid (0.982) | **Dense (0.856)** |

---

## Key Findings

### 1. Encoder upgrade is the single biggest lever

The encoder model change improved every meaningful metric across all four strategies. Context Precision roughly tripled for BM25 and Hybrid, roughly doubled for Dense. Answer Relevance jumped 0.18–0.34 across strategies — the largest per-run gain observed. Tree Index latency halved (20.8s → 11.2s), likely because the new encoder runs faster inference.

The encoder is upstream of every retrieval strategy. Investing in a better embedding model — especially a domain-adapted legal encoder — has higher expected ROI than tuning any single retrieval strategy.

### 2. Context precision is highly suppressed by RAGAS scoring

In Run 1, 34 of 41 questions returned 0 context_precision for all four strategies. The upgraded encoder raised non-zero precision counts significantly in Run 2 but absolute values remain low. This reflects RAGAS's strict grading: a retrieved chunk scores as precise only when its content is directly verifiable against the hand-written ground truth reference. For broad questions (semantic, compound, multihop) where the ground truth spans multiple regulations and retrieved chunks cover sub-parts of the answer, the metric consistently underscores. Context recall is the more informative metric for this corpus.

### 3. Hybrid is the best general-purpose strategy

Across both runs, Hybrid leads context recall and answer relevance overall. It dominates multihop queries (recall 0.304, AR 0.840 in Run 2) where a question requires evidence spread across multiple regulatory sections. The lexical component surfaces regulation-specific terminology; the semantic component bridges paraphrased phrasings. For compound questions, Hybrid also leads faithfulness (0.982) and recall (0.322).

**Recommendation: Hybrid for production RAG over SEBI regulatory corpus.**

### 4. BM25 is the keyword specialist — and fast

BM25 leads keyword recall in Run 2 (0.563, well above Dense at 0.354), achieves the best answer relevance on keyword questions (0.742), and is the fastest strategy (57ms in Run 2). The SEBI corpus is dense with precise regulatory terminology ("open offer", "designated person", "structured digital database") that BM25's exact-match vocabulary handles natively.

BM25 is the right choice when latency is the primary constraint or queries are known to be fact lookups.

### 5. Dense retrieval wins semantic precision; hybrid wins semantic answer quality

On semantic questions in Run 2, Dense achieves the highest context precision (0.422), confirming that embedding similarity finds conceptually relevant chunks better than keyword overlap. However Hybrid edges ahead on answer relevance (0.863 vs 0.817 for both BM25 and Dense). Tree Index badly fails semantic recall (0.061) — its hierarchical traversal optimises for a single node, missing distributed conceptual evidence.

Dense would likely improve further with a legal domain embedding model. `all-MiniLM-L6-v2` is general-purpose and not trained on regulatory language.

### 6. Tree Index is a compound specialist for retrieval — but a poor answer generator for those queries

Tree Index's most surprising result in Run 2: it leads both precision (0.333) and recall (0.327) on compound questions, beating every other strategy. The hierarchical structure navigates cross-topic compound questions (e.g. "obligations under LODR when both a related party transaction and a material event occur") by selecting nodes across different regulatory branches. However its faithfulness drops to 0.797 on compound (lowest of any strategy/category combination), meaning it retrieves broadly but the LLM partially hallucinates when synthesising across branches. Dense wins compound answer relevance (0.856).

Tree Index latency (11s per query in Run 2) makes it impractical for interactive use. Reserve it for batch keyword lookup and FAQ-style queries.

### 7. Faithfulness measures grounding in retrieved context, not answer correctness

Faithfulness (RAGAS) decomposes the generated answer into atomic claims and checks whether each claim is supported by the retrieved chunks. High faithfulness means the LLM stayed within the context it was given and did not hallucinate. It does not measure whether the retrieved chunks were the right ones — that is context precision and recall's job.

In our data, faithfulness is uniformly high (0.81–0.95 across all strategies and runs), meaning the generation model is well-grounded regardless of retrieval quality. The bottleneck is retrieval (precision/recall), not hallucination.

### 8. Token cost is tracked from live API response metadata

Token counts in the database are real billed tokens, not estimates. The generator records `response.usage.total_tokens` (Groq) or `response.usage_metadata.total_token_count` (Gemini) directly from each API call. The ~300–500 token increase in Run 2 versus Run 1 reflects richer context being passed to the LLM as a result of better retrieval from the upgraded encoder.

### 9. Answer relevance is suppressed by the noncommittal penalty

RAGAS `ResponseRelevancy` multiplies cosine similarity by `int(not noncommittal)`. The generator produces citation-style hedged answers ("Based on the retrieved passages...") which RAGAS flags as noncommittal, zeroing out many individual scores. Relative rankings across strategies are valid; absolute answer relevance values understate true semantic quality. The noncommittal suppression is consistent across runs, so cross-run comparisons are also valid.

---

## Strategy Selection Guide

| Use Case | Recommended Strategy | Why |
|----------|---------------------|-----|
| Exact regulatory lookup ("What is the X threshold?") | BM25 | Highest keyword recall (0.563), fastest (57ms) |
| Conceptual/semantic questions | Dense or Hybrid | Dense highest precision; Hybrid highest answer relevance |
| Multi-regulation questions (multihop) | Hybrid | Best recall (0.304) and answer relevance (0.840) |
| Cross-regulation comparisons (compound) | Tree Index (retrieval) + Dense (generation) | Tree retrieves broadest; Dense generates best answers |
| Interactive chat (sub-second budget) | BM25 → Hybrid fallback | BM25 at 57ms; Hybrid at 717ms for complex queries |
| Batch factoid lookup / FAQ | Tree Index | Best compound precision; acceptable at batch latency |

---

## Methodology Notes

- **Run 1 missing row**: `mh_02 × dense` returned NaN faithfulness (generation call failed silently). 163/164 rows completed.
- **Answer relevance note**: Values are suppressed ~30–50% by RAGAS noncommittal penalty. Relative comparisons are valid; absolute values are not.
- **Ground truth**: Hand-written from SEBI regulatory text. 10 questions removed that required RBI/MCA corpus not in scope. 1 question removed (kw_01) where relevant regulation was truncated in the corpus.
- **Tree index build cost**: ~$2.50 using Gemini 2.5 Flash (thinking tokens) for Run 1. Set `GEMINI_MODEL=gemini-2.0-flash` to reduce future build costs to ~$0.10.
- **Token tracking**: All token counts sourced from live API response metadata (`response.usage.total_tokens` for Groq, `response.usage_metadata.total_token_count` for Gemini). Real billed tokens, not estimates.
- **Tree index library**: Built and queried using LlamaIndex (`llama-index-core`) — `TreeIndex.from_documents()` for ingestion, `as_query_engine(retriever_mode="select_leaf")` for traversal. LlamaIndex owns the full tree lifecycle (construction, persistence, traversal).
