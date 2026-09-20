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
        })

    assert response.status_code == 200
    data = response.json()
    assert "filing_text" not in data
    assert data["ticker"] == "AAPL"
    assert data["question"] == "What is the outlook?"
    assert data["final_report"] == "Report content here"
    assert data["judge_score"] == {"overall": 10}
    assert data["retry_count"] == 0


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


def test_empty_question_returns_422():
    """Verify that an empty question fails min_length validation with 422."""
    response = client.post("/report", json={
        "ticker": "AAPL",
        "question": "",
        "judge_mode": "api",
    })
    assert response.status_code == 422
