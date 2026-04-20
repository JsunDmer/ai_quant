from fastapi.testclient import TestClient

from stock_mvp.api.main import create_app


def test_job_lifecycle_smoke():
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
    assert p2["status"] in ("queued", "running", "success", "failed")

