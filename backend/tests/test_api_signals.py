from fastapi.testclient import TestClient

from stock_mvp.api.main import create_app


def test_signals_latest_shape():
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/signals/latest?limit=5")
    assert r.status_code == 200
    payload = r.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)

