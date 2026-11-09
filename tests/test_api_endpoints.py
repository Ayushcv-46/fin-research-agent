from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_report_endpoint_excludes_filing_text():
    """Verify that /report returns allowlist fields and does not include filing_text."""
    mock_final_state = {
        "ticker": "AAPL",
        "question": "What is the outlook?",
        "filing_text": "RAW SECRET FILING TEXT THAT SHOULD NEVER BE EXPOSED",
        "final_report": "Report content here",
        "judge_score": {"overall": 10},
        "price_data": {"price": 150.0},
        "fundamentals": {"pe_ratio": 20},
        "confidence_label": "Correct",
        "confidence_reasoning": "Reasoning here",
        "retry_count": 0,
    }

    with patch("app.main.GRAPH.invoke", return_value=mock_final_state), \
         patch("app.main.save_report"):
        response = client.post("/report", json={
            "ticker": "AAPL",
            "question": "What is the outlook?",
            "judge_mode": "api",
            "search_mode": "hybrid",
            "retrieval_mode": "fixed",
        })

    assert response.status_code == 200
    data = response.json()
    assert "filing_text" not in data
    assert data["ticker"] == "AAPL"
    assert data["question"] == "What is the outlook?"
    assert data["final_report"] == "Report content here"
    assert data["judge_score"] == {"overall": 10}
    assert data["retry_count"] == 0
    assert data["search_mode"] == "hybrid"


def test_invalid_judge_mode_returns_422_post():
    """Verify that passing an invalid judge_mode to /report returns 422 Unprocessable Entity."""
    response = client.post("/report", json={
        "ticker": "AAPL",
        "question": "What is the outlook?",
        "judge_mode": "invalid_mode",
    })
    assert response.status_code == 422


def test_invalid_judge_mode_returns_422_stream():
    """Verify that passing an invalid judge_mode to /report/stream returns 422 Unprocessable Entity."""
    response = client.get("/report/stream?ticker=AAPL&question=What+is+outlook&judge_mode=invalid_mode")
    assert response.status_code == 422


def test_finetuned_judge_reports_missing_optional_runtime():
    response = client.post("/report", json={"ticker": "AAPL", "question": "outlook", "judge_mode": "finetuned"})
    assert response.status_code == 422
    assert "CUDA/Unsloth" in response.json()["detail"]


def test_empty_question_returns_422():
    """Verify that an empty question fails min_length validation with 422."""
    response = client.post("/report", json={
        "ticker": "AAPL",
        "question": "",
        "judge_mode": "api",
    })
    assert response.status_code == 422


def test_invalid_search_mode_returns_422():
    response = client.post("/report", json={"ticker": "AAPL", "question": "outlook", "search_mode": "unknown"})
    assert response.status_code == 422


def test_company_name_must_be_selected_from_directory():
    with patch("app.main._get_company_directory", return_value=[{"ticker": "DIS", "name": "The Walt Disney Company", "cik": "0001744489"}]):
        response = client.post("/report", json={"company_name": "Disney Corporation", "question": "What does this company do?"})
    assert response.status_code == 422


def test_company_search_prefers_exact_ticker():
    companies = [
        {"ticker": "A", "name": "A Example Holdings"},
        {"ticker": "AA", "name": "AA Example Inc"},
    ]
    with patch("app.main._get_company_directory", return_value=companies):
        response = client.get("/companies/search?q=AA")
    assert response.status_code == 200
    assert response.json()[0]["ticker"] == "AA"


def test_ticker_validation_accepts_sec_class_share_tickers():
    from app.main import validate_ticker
    assert validate_ticker("brk.b") == "BRK.B"
