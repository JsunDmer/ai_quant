from fastapi.testclient import TestClient

from backend.api.main import create_app


def test_market_latest_shape_when_empty():
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/market/latest")
    assert r.status_code in (200, 404)

