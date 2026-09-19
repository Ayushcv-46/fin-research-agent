from unittest.mock import patch, MagicMock
from db.persistence import save_report


def test_save_report_with_none_judge_score():
    mock_session = MagicMock()
    with patch("db.persistence.SessionLocal", return_value=mock_session):
        state = {
            "ticker": "AAPL",
            "question": "How is AAPL doing?",
            "final_report": "Report text",
            "judge_score": None,
            "retrieval_mode": "adaptive",
            "judge_mode": "api",
        }
        report = save_report(state)

        assert report.ticker == "AAPL"
        assert report.overall == -1
        assert report.grounding == -1
        assert mock_session.add.called
        assert mock_session.commit.called
        assert mock_session.close.called
