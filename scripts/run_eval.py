import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse, json, glob, uuid
from dotenv import load_dotenv
load_dotenv()

from src.retrieval.base import timed_retrieve
from src.retrieval.dense import DenseRetriever
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.tree_index import TreeIndexRetriever
from src.generation.generator import generate_from_env
from src.evaluation.ragas_runner import run_ragas_from_env
from src.evaluation.logger import init_db, log_row

STRATEGIES = ["dense", "bm25", "hybrid", "tree_index"]

def load_chunks(chunks_dir):
    chunks = []
    # Search for any JSON files that end in _chunks.json
    for path in sorted(glob.glob(os.path.join(chunks_dir, "*_chunks.json"))):
        with open(path) as f:
            chunks.extend(json.load(f))
    return chunks

def load_retrievers(chunks, index_dir, strategies):
    retrievers = {}
    if "dense" in strategies:
        r = DenseRetriever(chunks)
        r.load_index(os.path.join(index_dir, "dense.index"))
        retrievers["dense"] = r
    if "bm25" in strategies:
        r = BM25Retriever(chunks)
        r.load_index(os.path.join(index_dir, "bm25.index"))
        retrievers["bm25"] = r
    if "hybrid" in strategies:
        r = HybridRetriever(chunks)
        r.load_index(os.path.join(index_dir, "hybrid.index"))
        retrievers["hybrid"] = r
    if "tree_index" in strategies:
        r = TreeIndexRetriever(chunks)
        r.load_index(os.path.join(index_dir, "tree_index"))
        retrievers["tree_index"] = r
    return retrievers

def main():
    parser = argparse.ArgumentParser(description="Run RAG Arena evaluation")
    parser.add_argument("--chunks-dir", default="data/chunks")
    parser.add_argument("--index-dir", default="data/indexes")
    parser.add_argument("--questions", default="data/eval/questions.json")
    parser.add_argument("--ground-truth", default="data/eval/ground_truth.json")
    parser.add_argument("--db", default="results/evals.db")
    parser.add_argument("--run-id", default=None, help="Run identifier (auto-generated if not set)")
    parser.add_argument("--strategies", nargs="+", default=STRATEGIES, choices=STRATEGIES)
    parser.add_argument("--limit", type=int, default=None, help="Only run first N questions")
    parser.add_argument("--k", type=int, default=5, help="Chunks to retrieve per strategy")
    args = parser.parse_args()

    run_id = args.run_id or f"run_{uuid.uuid4().hex[:8]}"
    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    init_db(args.db)

    print(f"Run ID: {run_id}")

    # Load questions and ground truth
    if not os.path.exists(args.questions):
        print(f"Questions file not found: {args.questions}")
        sys.exit(1)
    
    with open(args.questions) as f:
        questions = json.load(f)
    
    ground_truths = {}
    if os.path.exists(args.ground_truth):
        with open(args.ground_truth) as f:
            ground_truths = json.load(f)  # dict: query_id -> answer string

    if args.limit:
        questions = questions[:args.limit]

    total_calls = len(questions) * len(args.strategies)
    print(f"Questions: {len(questions)} | Strategies: {args.strategies} | Total LLM calls: ~{total_calls * 2}")
    print("Proceed? [y/N] ", end="")
    try:
        user_input = input().strip().lower()
    except EOFError:
        user_input = "n"
        
    if user_input != "y":
        print("Aborted.")
        return

    # Load chunks and indexes
    print("Loading chunks...")
    chunks = load_chunks(args.chunks_dir)
    if not chunks:
        print(f"No chunks found in {args.chunks_dir}. Run scripts/ingest.py first.")
        sys.exit(1)
    print(f"Loaded {len(chunks)} chunks.")

    print("Loading indexes...")
    try:
        retrievers = load_retrievers(chunks, args.index_dir, args.strategies)
    except Exception as e:
        print(f"Error loading indexes: {e}")
        print("Ensure you have run scripts/build_indexes.py first.")
        sys.exit(1)
        
    print(f"Loaded: {list(retrievers.keys())}")

    # Eval loop
    for i, q in enumerate(questions):
        query_id = q["id"]
        query = q["question"]
        ground_truth = ground_truths.get(query_id, "")
        print(f"\n[{i+1}/{len(questions)}] {query_id}: {query[:60]}...")

        for strategy, retriever in retrievers.items():
            try:
                # 1. Retrieval
                result = timed_retrieve(retriever, query, k=args.k)
                
                # 2. Generation
                gen = generate_from_env(query, result["chunks"])
                
                # 3. RAGAS Evaluation
                scores = run_ragas_from_env(query, result["chunks"], gen["answer"], ground_truth)

                token_cost = result["token_cost"] + gen["token_cost"]

                # 4. Logging
                log_row(args.db, run_id, {
                    "query_id": query_id,
                    "strategy": strategy,
                    "context_precision": scores["context_precision"],
                    "context_recall": scores["context_recall"],
                    "faithfulness": scores["faithfulness"],
                    "answer_relevance": scores["answer_relevance"],
                    "latency_ms": result["latency_ms"],
                    "token_cost": token_cost,
                })
                print(f"  {strategy}: prec={scores['context_precision']:.2f} "
                      f"rec={scores['context_recall']:.2f} "
                      f"faith={scores['faithfulness']:.2f} "
                      f"rel={scores['answer_relevance']:.2f} "
                      f"latency={result['latency_ms']:.0f}ms")
            except Exception as e:
                print(f"  {strategy}: FAILED — {e}")

    print(f"\nDone. Results in {args.db} (run_id={run_id})")

if __name__ == "__main__":
    main()
