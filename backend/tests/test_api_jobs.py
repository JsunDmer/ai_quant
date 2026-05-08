from fastapi.testclient import TestClient

from backend.api import jobs as jobs_mod
from backend.api.main import create_app


def test_job_lifecycle_smoke(monkeypatch):
    def fake_pipeline(**kwargs):
        return {
            "status": "ok",
            "trade_date": "2026-04-21",
            "data_date": "2026-04-21",
            "errors": [],
            "sector_recommendations": [{"sector_name": "半导体"}],
            "sector_top_stocks": {"半导体": [{"code": "688001"}]},
            "stock_signals": [],
            "auction_filtered_out": [],
            "diagnostics": {
                "candidate_pick": {"candidate_count_after_auction": 1},
                "signal_generation": {"buy_signal_count": 0},
            },
        }

    monkeypatch.setattr(jobs_mod, "run_post_close_pipeline", fake_pipeline)

    app = create_app()
    c = TestClient(app)

    r = c.post(
        "/api/jobs/analysis",
        json={"ai_enabled": False, "refresh_realtime_only": True},
    )
    assert r.status_code in (200, 202)
    payload = r.json()
    assert "task_id" in payload
    assert payload["status"] in ("queued", "running", "success")

    task_id = payload["task_id"]
    r2 = c.get(f"/api/jobs/{task_id}")
    assert r2.status_code == 200
    p2 = r2.json()
    assert p2["task_id"] == task_id
    assert p2["status"] == "success"
    assert p2["result_summary"]["sectors"] == 1
    assert p2["result_summary"]["sector_top_stocks"] == 1
    assert p2["result_summary"]["signals"] == 0
    assert p2["result_summary"]["diagnostics"]["candidate_pick"]["candidate_count_after_auction"] == 1


def test_job_failure_records_error(monkeypatch):
    def fail_pipeline(**kwargs):
        raise RuntimeError("pipeline boom")

    monkeypatch.setattr(jobs_mod, "run_post_close_pipeline", fail_pipeline)

    app = create_app()
    c = TestClient(app)

    r = c.post(
        "/api/jobs/analysis",
        json={"ai_enabled": False, "refresh_realtime_only": True},
    )
    assert r.status_code in (200, 202)

    task_id = r.json()["task_id"]
    r2 = c.get(f"/api/jobs/{task_id}")
    assert r2.status_code == 200
    p2 = r2.json()
    assert p2["status"] == "failed"
    assert p2["error"] == "pipeline boom"
    assert p2["result_summary"] is None

