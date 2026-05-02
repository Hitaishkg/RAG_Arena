# Chunking Analysis — RAG Arena

## Strategy

**Type:** Sentence-boundary chunking with token budget
**Implementation:** `src/ingestion/chunker.py`

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Chunk size | 512 tokens | Fits one full regulatory sub-clause; precise enough for retrieval |
| Overlap | 64 tokens | ~2–3 sentences; preserves provisos that start a new chunk |
| Tokenizer | tiktoken cl100k_base | GPT-4 token counting; consistent with embedding models |
| Sentence split | NLTK sent_tokenize | Never cuts mid-sentence — critical for legal text |
| Granularity | Per page | Page number stays exact for every chunk; page boundary resets context |
| Section detection | First 5 lines of page | All-caps / numbered / Roman numeral heading patterns |

**Why sentence boundaries matter for this corpus:** Legal provisions are constructed so that any mid-sentence cut destroys meaning. "An acquirer who acquires... shall not be required to make an open offer..." split at an arbitrary position produces two meaningless fragments. NLTK sentence tokenization is the minimum correctness requirement for SEBI/RBI regulatory text.

**Why not recursive/hierarchical chunking:** This is a benchmarking project. Chunking is a controlled variable — identical chunks are fed to all 4 retrieval strategies so eval score differences reflect retrieval algorithm quality, not chunking quality. A simple, deterministic baseline is the right choice here.

---

## Corpus Stats (after ingestion)

| Document | Pages | Chunks |
|----------|-------|--------|
| sebi_lodr_2015 | 101 | 173 |
| sebi_pit_2015 | 80 | 99 |
| sebi_icdr_2018 | 471 | 700 |
| sebi_sast_2011 | 79 | 104 |
| sebi_mutual_fund_reg | 160 | 291 |
| **Total** | **891** | **1,367** |

RBI docs (rbi_kyc_master_dir, rbi_nbfc_master_dir) — not available; CDN geo-blocks programmatic download. 8 eval questions affected.

---

## Observed Strengths

- Sentence boundary guarantee works well — no truncated provisions in any of the 5 docs
- 512-token budget cleanly captures most SEBI sub-regulations (typically 3–8 sentences)
- BM25 retrieval will be highly accurate for keyword questions — specific terms like "twenty-five per cent", "forty-five days", "cooling-off" appear fully intact within single chunks
- LODR (173 chunks, dense regulation structure) had excellent chunk coherence — most chunks mapped to a complete Regulation or Schedule provision

---

## Observed Weaknesses

### 1. Footnote contamination (significant noise)
SEBI/RBI PDFs embed amendment footnotes inline with the text, not in a separate footer area. The PDF extractor captures them as part of the page body. Example from SAST:

```
...entitling them to exercise twenty-five per cent or more...
15 Inserted by the Securities and Exchange Board of India (Substantial
Acquisition of Shares and Takeovers) (Third Amendment) Regulations, 2021
w.e.f. 6-12-2021...
```

Approximately 30–40% of ICDR chunks (the most amended document, 471 pages) contain this noise. Impact:
- Dense embedding similarity diluted — footnote text pulls the embedding away from the actual provision meaning
- Generator may cite "[15]" or "[23]" as if they are passage references — confuses the answer
- RAGAS faithfulness scoring may flag footnote text as unsupported claims

**Fix considered for future:** Strip lines matching `^\d+\s+(Inserted|Substituted|Omitted|Renumbered) by` before chunking.

### 2. Page-level processing breaks cross-page regulations
The chunker resets at every page boundary. There is zero overlap between the last chunk of page N and the first chunk of page N+1.

Example: SAST Regulation 3 spans pages 9–11. Sub-regulation (1) — the 25% trigger — is on page 9. Sub-regulation (2) — the 5% creep limit — is on page 9–10. The Explanation is on page 10. The full picture of the regulation is spread across 3 chunks with no cross-page continuity signal.

Impact on retrieval:
- BM25: will find the right page but may miss the full context
- Dense: embedding of chunk captures sub-regulation in isolation; may miss inter-connected provisions
- Hybrid: same as Dense/BM25 limitations
- **Tree Index: expected advantage here** — the tree building phase summarises multiple chunks, so cross-page regulations get synthesised at a higher tree level. This is one of the key hypotheses to validate in the eval.

### 3. Section detection mostly fails on SEBI docs
`detect_section()` looks for all-caps or numbered headings in the first 5 lines of a page. SEBI uses mixed-case headings like:

```
Minimum Public Shareholding.
38. The listed entity shall comply...
```

`"Minimum Public Shareholding."` does not match the all-caps pattern. Result: `section` field is an empty string for the majority of chunks across all 5 documents. The section metadata intended to help retrieval is effectively unused.

Impact: Minor — the `section` field is stored in the Chunk TypedDict but none of the current retrieval strategies use it for filtering or boosting. It would matter more in a production system.

---

## Impact on Eval Hypotheses

| Retrieval Strategy | Expected Impact of Weaknesses |
|-------------------|-------------------------------|
| BM25 | Footnote noise adds irrelevant term frequency; cross-page breaks limit multi-clause recall |
| Dense | Footnote contamination dilutes embeddings; cross-page breaks hurt semantic completeness |
| Hybrid | Inherits both BM25 and Dense limitations, but reranker (CrossEncoder) may partially recover |
| Tree Index | Best positioned for cross-page regulations; footnote noise affects leaf summaries but may be filtered at tree levels |

**Key hypothesis to verify in eval:** Tree Index should show higher context_recall on multi-hop questions precisely because it handles cross-page regulation context better than flat retrieval.

---

## Future Improvements (post v1.0)
1. Strip amendment footnotes before chunking (regex on `^\d+\s+(Inserted|Substituted|Omitted)`)
2. Cross-page overlap: carry last N tokens from page K into the first chunk of page K+1
3. Regulation-aware chunking: split at regulation/sub-regulation boundaries rather than sentence/token budget
4. Fix section detection: use the regulation number pattern (e.g., `^(\d+)\.\s+[A-Z]`) as a section identifier
