import os, glob, json, concurrent.futures, time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import Field
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

_state: dict = {}  # module-level dict storing loaded chunks + retrievers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    from src.retrieval.dense import DenseRetriever
    from src.retrieval.bm25 import BM25Retriever
    from src.retrieval.hybrid import HybridRetriever
    from src.retrieval.tree_index import TreeIndexRetriever

    chunks_dir = os.getenv("CHUNKS_DIR", "data/chunks")
    index_dir = os.getenv("INDEX_DIR", "data/indexes")

    # Load all chunks from *_chunks.json files
    chunks = []
    for path in sorted(glob.glob(os.path.join(chunks_dir, "*_chunks.json"))):
        with open(path) as f:
            chunks.extend(json.load(f))

    retrievers = {}

    # Dense
    try:
        r = DenseRetriever(chunks)
        r.load_index(os.path.join(index_dir, "dense.index"))
        retrievers["dense"] = r
    except Exception as e:
        print(f"[startup] dense: FAILED — {e}")

    # BM25
    try:
        r = BM25Retriever(chunks)
        r.load_index(os.path.join(index_dir, "bm25.index"))
        retrievers["bm25"] = r
    except Exception as e:
        print(f"[startup] bm25: FAILED — {e}")

    # Hybrid
    try:
        r = HybridRetriever(chunks)
        r.load_index(os.path.join(index_dir, "hybrid.index"))
        retrievers["hybrid"] = r
    except Exception as e:
        print(f"[startup] hybrid: FAILED — {e}")

    # Tree Index — graceful: skip if not built
    tree_path = os.path.join(index_dir, "tree_index")
    if os.path.isdir(tree_path):
        try:
            r = TreeIndexRetriever(chunks)
            r.load_index(tree_path)
            retrievers["tree_index"] = r
        except Exception as e:
            print(f"[startup] tree_index: FAILED — {e}")
    else:
        print("[startup] tree_index: not built — skipping")

    _state["chunks"] = chunks
    _state["retrievers"] = retrievers
    print(f"[startup] loaded {len(chunks)} chunks, strategies: {list(retrievers.keys())}")

    yield  # app is live

    # --- shutdown ---
    _state.clear()

class QueryRequest(BaseModel):
    question: str
    k: int = Field(default=5, ge=1, le=20)

class ChunkResult(BaseModel):
    id: str
    text: str
    doc_id: str
    page: int
    section: str

class StrategyResult(BaseModel):
    answer: str
    chunks: list[ChunkResult]
    latency_ms: float
    token_cost: int
    error: Optional[str] = None

class QueryResponse(BaseModel):
    question: str
    results: dict[str, StrategyResult]
    available_strategies: list[str]

app = FastAPI(title="RAG Arena", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML frontend) — only if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "chunks_loaded": len(_state.get("chunks", [])),
        "strategies": list(_state.get("retrievers", {}).keys()),
    }

@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    from src.retrieval.base import timed_retrieve
    from src.generation.generator import generate_from_env

    retrievers = _state.get("retrievers", {})
    if not retrievers:
        raise HTTPException(status_code=503, detail="No retrievers loaded")

    def run_strategy(name: str, retriever):
        try:
            t0 = time.monotonic()
            result = timed_retrieve(retriever, req.question, k=req.k)
            gen = generate_from_env(req.question, result["chunks"])
            total_ms = (time.monotonic() - t0) * 1000
            return name, StrategyResult(
                answer=gen["answer"],
                chunks=[ChunkResult(**c) for c in result["chunks"]],
                latency_ms=round(total_ms, 1),
                token_cost=result["token_cost"] + gen["token_cost"],
            )
        except Exception as e:
            return name, StrategyResult(
                answer="",
                chunks=[],
                latency_ms=0.0,
                token_cost=0,
                error=str(e),
            )

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(retrievers)) as pool:
        futures = {pool.submit(run_strategy, name, r): name for name, r in retrievers.items()}
        for future in concurrent.futures.as_completed(futures):
            name, res = future.result()
            results[name] = res

    return QueryResponse(
        question=req.question,
        results=results,
        available_strategies=list(retrievers.keys()),
    )

ACTIVE_RUN_ID = "run_023c3905"

@app.get("/results")
def results():
    from src.evaluation.logger import fetch_run
    db_path = os.getenv("EVAL_DB", "results/evals.db")
    if not os.path.exists(db_path):
        return {"rows": [], "summary": {}}

    rows = fetch_run(db_path, ACTIVE_RUN_ID)
    
    # Aggregate per strategy
    summary = {}
    for row in rows:
        strat = row["strategy"]
        if strat not in summary:
            summary[strat] = {
                "context_precision": [], "context_recall": [],
                "faithfulness": [], "answer_relevance": [],
                "latency_ms": [], "token_cost": [],
            }
        for k in summary[strat]:
            if row.get(k) is not None:
                summary[strat][k].append(row[k])
    
    # Compute averages
    averages = {}
    for strat, metrics in summary.items():
        averages[strat] = {k: (sum(v) / len(v) if v else None) for k, v in metrics.items()}
    
    return {"rows": rows[:200], "summary": averages}

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")
