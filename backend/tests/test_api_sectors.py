from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.routes import sectors as sectors_route


def test_sectors_latest_shape(monkeypatch):
    rec = SimpleNamespace(
        trade_date="2026-04-21",
        sector_name="电池",
        score=35.0,
        bucket="watch",
        reasons_json='["资金净流入"]',
    )
    monkeypatch.setattr(sectors_route.db, "get_latest_ai_sector_analysis", lambda: [])
    monkeypatch.setattr(sectors_route.db, "get_latest_sector_recommendations", lambda: [rec])
    monkeypatch.setattr(sectors_route.db, "get_stock_signals", lambda trade_date: [])
    monkeypatch.setattr(sectors_route.db, "get_latest_stock_signals", lambda limit=500: [])
    monkeypatch.setattr(sectors_route.db, "get_sector_stocks", lambda sector_name, trade_date=None: [])

    app = create_app()
    c = TestClient(app)
    r = c.get("/api/sectors/latest")
    assert r.status_code == 200
    payload = r.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["sector_name"] == "电池"
    assert "top_stocks" in item
    assert isinstance(item["top_stocks"], list)
    assert item.get("stocks_source") in {"none", "signal", "sector_cache"}

