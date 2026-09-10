from app import app


def test_analyze_event_high_activity():
    data = {
        "file_count": 90,
        "operation_frequency": 95,
        "unusual_time_access": 85,
        "change_size": 100,
    }

    with app.test_client() as client:
        response = client.post(
            "/analyze-event",
            json=data,
        )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload is not None

    assert payload["input_event"] == {
        "file_count": 90,
        "operation_frequency": 95,
        "unusual_time_access": 85,
        "change_size": 100.0,
        "event_type": "UNKNOWN",
        "file_path": "UNKNOWN",
    }

    assert "raw_scores" in payload
    assert "normalized_scores" in payload
    assert "final_score" in payload
    assert "risk_level" in payload
    assert "recommended_action" in payload

    assert isinstance(
        payload["raw_scores"],
        dict,
    )

    assert isinstance(
        payload["normalized_scores"],
        dict,
    )

    assert isinstance(
        payload["final_score"],
        float,
    )

    assert isinstance(
        payload["risk_level"],
        str,
    )

    assert isinstance(
        payload["recommended_action"],
        str,
    )