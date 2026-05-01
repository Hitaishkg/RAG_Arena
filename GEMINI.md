# RAG Arena — Gemini CLI Instructions

## What this project is
A 4-way RAG retrieval benchmarking system. Full spec in rag-arena-spec.md.
Read rag-arena-spec.md before doing anything. Read CODEBASE_GRAPH.md before reading source files.

## Development workflow
Follow the multi-agent structure in rag-arena-spec.md Section 15.
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
Role definitions are in rag-arena-spec.md Section 15.

ACTIVE ROLE: Architect

## Stack
Python 3.11+, Gemini 1.5 Flash (primary), Groq/Llama 3.3 70B (fallback),
FAISS, rank-bm25, llama-index, RAGAS, Streamlit, SQLite.
