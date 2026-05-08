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


def test_recommendation_compare_shape(monkeypatch):
    monkeypatch.setattr(
        evaluation_route.recommendation_evaluator,
        "get_type_source_comparison",
        lambda **kwargs: [
            {
                "recommendation_type": "stock_signal",
                "source": "signal",
                "sample_count": 12,
                "hit_rate_5d": 58.3,
                "avg_return_5d": 1.2,
                "avg_excess_return_5d": 0.4,
            }
        ],
    )
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/evaluation/recommendations/compare")
    assert r.status_code == 200
    payload = r.json()
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["recommendation_type"] == "stock_signal"


def test_portfolio_suggest_shape(monkeypatch):
    monkeypatch.setattr(
        evaluation_route.portfolio_builder,
        "suggest",
        lambda **kwargs: {"trade_date": "2024-01-15", "summary": {"selected_count": 3}, "items": []},
    )
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/evaluation/portfolio/suggest?top_n=6")
    assert r.status_code == 200
    payload = r.json()
    assert payload["summary"]["selected_count"] == 3


def test_simulation_run_full(monkeypatch):
    monkeypatch.setattr(evaluation_route.trade_simulator, "run_full_simulation", lambda: {"created": 5, "closed": 2})
    app = create_app()
    c = TestClient(app)
    r = c.post("/api/evaluation/simulation/run")
    assert r.status_code == 200
    payload = r.json()
    assert payload["mode"] == "full"
    assert payload["created"] == 5


def test_optimizer_run_shape(monkeypatch):
    monkeypatch.setattr(
        evaluation_route.strategy_parameter_optimizer,
        "run",
        lambda **kwargs: {"status": "ok", "sample_count": 88, "best": {"name": "trial_2"}},
    )
    app = create_app()
    c = TestClient(app)
    r = c.post("/api/evaluation/optimizer/run?trials=10")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["sample_count"] == 88

