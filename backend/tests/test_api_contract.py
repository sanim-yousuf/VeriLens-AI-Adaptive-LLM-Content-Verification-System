from fastapi.testclient import TestClient

from app.main import create_app


def test_analysis_response_matches_frontend_contract() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/analyses",
        json={
            "type": "text",
            "content": "URGENT share now! Secret cure guaranteed 100% true. Forward this to everyone.",
            "analysis_mode": "offline",
            "user_context": {"region": "BD", "audience": "general"},
        },
    )

    assert response.status_code == 201
    payload = response.json()

    expected_keys = {
        "analysis_id",
        "schema_version",
        "input_type",
        "topic",
        "language",
        "trust_score",
        "risk_level",
        "confidence",
        "misinformation_probability",
        "manipulation_score",
        "source_score",
        "evidence_quality",
        "score_breakdown",
        "reasoning",
        "highlight_spans",
        "agent_findings",
        "visual_authenticity",
        "risk_factors",
        "claim_checks",
        "manipulation_patterns",
        "ai_generated_likelihood",
        "viral_risk",
        "regional_context",
        "community_signal",
        "trust_timeline",
        "expert_notes",
        "recommended_action",
        "summary",
        "uncertainty",
        "moderation",
        "cost",
        "source_url",
        "region",
        "evidence_vs_inference",
        "raw_signals",
    }
    assert expected_keys.issubset(payload.keys())
    assert payload["cost"]["openai_used"] is False
    assert payload["cost"]["model_used"] == "offline-heuristics"
    assert payload["claim_checks"]
    assert payload["risk_factors"]
    assert payload["agent_findings"]
    assert any(event["stage"] == "openai_analysis" for event in payload["trust_timeline"])


def test_cached_analysis_id_can_be_explained() -> None:
    client = TestClient(create_app())
    request_payload = {
        "type": "text",
        "content": "According to an official report in 2025, school results were published.",
        "analysis_mode": "offline",
    }

    first = client.post("/v1/analyses", json=request_payload).json()
    second_response = client.post("/v1/analyses", json=request_payload)
    second = second_response.json()

    assert second_response.status_code == 201
    assert first["analysis_id"] != second["analysis_id"]
    assert second["cost"]["cache_hit"] is True

    explain_response = client.post(
        f"/v1/analyses/{second['analysis_id']}/explain",
        json={"question": "Why is the score this level?"},
    )
    assert explain_response.status_code == 200
    assert explain_response.json()["analysis_id"] == second["analysis_id"]


def test_feedback_updates_community_signal() -> None:
    client = TestClient(create_app())
    analysis = client.post(
        "/v1/analyses",
        json={
            "type": "text",
            "content": "Breaking election report says a minister announced a major result in 2025.",
            "analysis_mode": "offline",
        },
    ).json()

    feedback = client.post(
        "/v1/feedback",
        json={
            "analysis_id": analysis["analysis_id"],
            "user_rating": 4,
            "corrected_risk_level": "medium",
            "notes": "Looks reasonable.",
        },
    )
    assert feedback.status_code == 202
    assert feedback.json()["report_count"] == 1
    assert feedback.json()["consensus"] == "medium"

    updated = client.get(f"/v1/analyses/{analysis['analysis_id']}").json()
    assert updated["community_signal"]["report_count"] == 1
    assert updated["community_signal"]["consensus"] == "medium"
