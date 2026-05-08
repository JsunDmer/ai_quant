from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.routes import evaluation as evaluation_route


def test_evaluation_summary_shape():
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/evaluation/summary")
    assert r.status_code == 200
    payload = r.json()
    assert "summary" in payload


def test_recommendation_summary_shape(monkeypatch):
    monkeypatch.setattr(
        evaluation_route.recommendation_evaluator,
        "get_summary",
        lambda **kwargs: {
            "total_recommendations": 12,
            "t1": {"evaluated_count": 10, "hit_count": 6, "hit_rate": 60.0, "avg_return": 1.2, "avg_excess_return": 0.4},
            "t3": {"evaluated_count": 10, "hit_count": 7, "hit_rate": 70.0, "avg_return": 2.8, "avg_excess_return": 0.9},
            "t5": {"evaluated_count": 8, "hit_count": 6, "hit_rate": 75.0, "avg_return": 4.1, "avg_excess_return": 1.2},
        },
    )
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/evaluation/recommendations/summary")
    assert r.status_code == 200
    payload = r.json()
    assert payload["summary"]["total_recommendations"] == 12
    assert payload["summary"]["t1"]["hit_rate"] == 60.0


def test_recommendation_run_recent(monkeypatch):
    monkeypatch.setattr(evaluation_route.recommendation_evaluator, "evaluate_recent", lambda recent_days: 7)
    app = create_app()
    c = TestClient(app)
    r = c.post("/api/evaluation/recommendations/run?recent_days=20")
    assert r.status_code == 200
    payload = r.json()
    assert payload["mode"] == "recent_days"
    assert payload["recent_days"] == 20
    assert payload["evaluated"] == 7

