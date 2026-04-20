from fastapi.testclient import TestClient

from api.app import create_app


def test_sectors_latest_shape():
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/sectors/latest")
    assert r.status_code == 200
    payload = r.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)

