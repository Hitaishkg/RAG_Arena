import pytest
from unittest.mock import patch, MagicMock
from src.generation.generator import generate
from src.evaluation.logger import init_db, log_row, fetch_run, fetch_all

# --- Generator Tests ---

def test_generate_uses_groq_when_key_set():
    """Groq is called when groq_api_key is provided."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Test answer"
    mock_response.usage.total_tokens = 100

    with patch("groq.Groq") as MockGroq:
        MockGroq.return_value.chat.completions.create.return_value = mock_response
        result = generate(
            query="What is SEBI?",
            chunks=[{"doc_id": "d1", "page": 1, "text": "SEBI regulates securities."}],
            groq_api_key="fake_key",
        )

    assert result["answer"] == "Test answer"
    assert result["token_cost"] == 100
    assert "llama" in result["model_used"]

def test_generate_falls_back_to_gemini_on_groq_failure():
    """Falls back to Gemini when Groq raises an exception."""
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "Gemini answer"
    mock_gemini_response.usage_metadata.total_token_count = 200

    with patch("groq.Groq") as MockGroq, \
         patch("google.genai.Client") as MockGenai:
        MockGroq.return_value.chat.completions.create.side_effect = Exception("rate limit")
        MockGenai.return_value.models.generate_content.return_value = mock_gemini_response
        result = generate(
            query="What is SEBI?",
            chunks=[{"doc_id": "d1", "page": 1, "text": "SEBI regulates securities."}],
            groq_api_key="fake_key",
            google_api_key="fake_google_key",
        )

    assert result["answer"] == "Gemini answer"
    assert result["token_cost"] == 200

def test_generate_result_fields():
    """generate() always returns answer, token_cost, model_used."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Answer"
    mock_response.usage.total_tokens = 50

    with patch("groq.Groq") as MockGroq:
        MockGroq.return_value.chat.completions.create.return_value = mock_response
        result = generate("q", [{"doc_id": "d", "page": 1, "text": "t"}], groq_api_key="k")

    assert set(result.keys()) == {"answer", "token_cost", "model_used"}
    assert isinstance(result["answer"], str)
    assert isinstance(result["token_cost"], int)


# --- Logger Tests ---

def test_logger_init_and_log(tmp_path):
    """init_db creates table; log_row writes a row; fetch_run retrieves it."""
    db = str(tmp_path / "test.db")
    init_db(db)
    log_row(db, "run_001", {
        "query_id": "q1", "strategy": "dense",
        "context_precision": 0.8, "context_recall": 0.7,
        "faithfulness": 0.9, "answer_relevance": 0.85,
        "latency_ms": 120.5, "token_cost": 300,
    })
    rows = fetch_run(db, "run_001")
    assert len(rows) == 1
    assert rows[0]["strategy"] == "dense"
    assert rows[0]["context_precision"] == 0.8

def test_logger_multiple_rows(tmp_path):
    """Multiple rows for different strategies are stored and retrieved correctly."""
    db = str(tmp_path / "test.db")
    init_db(db)
    for strategy in ["dense", "bm25", "hybrid", "tree_index"]:
        log_row(db, "run_002", {
            "query_id": "q1", "strategy": strategy,
            "context_precision": 0.5, "context_recall": 0.5,
            "faithfulness": 0.5, "answer_relevance": 0.5,
            "latency_ms": 100.0, "token_cost": 100,
        })
    rows = fetch_all(db)
    assert len(rows) == 4
    strategies = {r["strategy"] for r in rows}
    assert strategies == {"dense", "bm25", "hybrid", "tree_index"}
