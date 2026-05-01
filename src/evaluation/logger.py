import sqlite3
from typing import Any

def init_db(db_path: str) -> None:
    """
    Create the database file and eval_results table if they don't exist.
    Uses CREATE TABLE IF NOT EXISTS. Safe to call multiple times.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                query_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                context_precision REAL,
                context_recall REAL,
                faithfulness REAL,
                answer_relevance REAL,
                latency_ms REAL,
                token_cost INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

def log_row(db_path: str, run_id: str, row: dict[str, Any]) -> None:
    """
    Insert one EvalRow into eval_results.
    row keys: query_id, strategy, context_precision, context_recall,
              faithfulness, answer_relevance, latency_ms, token_cost
    run_id is passed separately and written to the run_id column.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT INTO eval_results (
                run_id, query_id, strategy, context_precision, context_recall,
                faithfulness, answer_relevance, latency_ms, token_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            row["query_id"],
            row["strategy"],
            row.get("context_precision"),
            row.get("context_recall"),
            row.get("faithfulness"),
            row.get("answer_relevance"),
            row.get("latency_ms"),
            row.get("token_cost")
        ))

def fetch_all(db_path: str) -> list[dict[str, Any]]:
    """
    Return all rows from eval_results as a list of dicts.
    Each dict has all column names as keys.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM eval_results")
        return [dict(row) for row in cursor.fetchall()]

def fetch_run(db_path: str, run_id: str) -> list[dict[str, Any]]:
    """
    Return all rows for a specific run_id.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM eval_results WHERE run_id = ?", (run_id,))
        return [dict(row) for row in cursor.fetchall()]
