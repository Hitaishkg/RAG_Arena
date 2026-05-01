# Codebase Graph — RAG Arena

Last updated: 2026-04-30 | Phase: 0 - Initializing

## File Registry

| File | Purpose | Exports | Status | Phase |
|------|---------|---------|--------|-------|
| rag-arena-spec.md | Project Specification | - | ✅ Reviewed | 0 |
| GEMINI.md | Agent Instructions | - | ✅ Created | 0 |
| CODEBASE_GRAPH.md | Token Management Graph | - | ✅ Created | 0 |

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

(To be populated as we build)

## Review Status

| File | Reviewer verdict | Security verdict | Notes |
|------|-----------------|-----------------|-------|
| rag-arena-spec.md | ✅ Approved | ✅ Clean | Source of truth |
