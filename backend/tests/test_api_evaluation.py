from fastapi.testclient import TestClient

from stock_mvp.api.main import create_app


def test_evaluation_summary_shape():
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/evaluation/summary")
    assert r.status_code == 200
    payload = r.json()
    assert "summary" in payload

