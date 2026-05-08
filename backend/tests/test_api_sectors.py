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
    monkeypatch.setattr(sectors_route.db, "get_ai_sector_analysis", lambda trade_date: [])
    monkeypatch.setattr(sectors_route.db, "get_latest_sector_recommendations", lambda: [rec])
    monkeypatch.setattr(sectors_route.db, "get_stock_signals", lambda trade_date: [])
    monkeypatch.setattr(sectors_route.db, "get_latest_stock_signals", lambda limit=500: [])
    monkeypatch.setattr(sectors_route.db, "get_sector_stock_recommendations", lambda trade_date: [])
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
    assert item.get("stocks_source") in {"none", "signal", "sector_candidate", "sector_cache"}


def test_sectors_latest_prefers_sector_candidate_when_no_signal(monkeypatch):
    rec = SimpleNamespace(
        trade_date="2026-04-21",
        sector_name="电池",
        score=35.0,
        bucket="watch",
        reasons_json='["资金净流入"]',
    )
    sector_candidate = SimpleNamespace(
        trade_date="2026-04-21",
        sector_name="电池",
        stock_code="300750",
        stock_name="宁德时代",
        score=5.2,
        rank_no=1,
        price=198.5,
        change_pct=2.3,
        reason="板块内领涨2.3%",
        source="sector_candidate",
    )

    monkeypatch.setattr(sectors_route.db, "get_latest_ai_sector_analysis", lambda: [])
    monkeypatch.setattr(sectors_route.db, "get_ai_sector_analysis", lambda trade_date: [])
    monkeypatch.setattr(sectors_route.db, "get_latest_sector_recommendations", lambda: [rec])
    monkeypatch.setattr(sectors_route.db, "get_stock_signals", lambda trade_date: [])
    monkeypatch.setattr(sectors_route.db, "get_latest_stock_signals", lambda limit=500: [])
    monkeypatch.setattr(
        sectors_route.db,
        "get_sector_stock_recommendations",
        lambda trade_date: [sector_candidate],
    )
    monkeypatch.setattr(sectors_route.db, "get_sector_stocks", lambda sector_name, trade_date=None: [])

    app = create_app()
    c = TestClient(app)
    r = c.get("/api/sectors/latest")
    assert r.status_code == 200
    payload = r.json()
    item = payload["items"][0]
    assert payload["trade_date"] == "2026-04-21"
    assert item["stocks_source"] == "sector_candidate"
    assert len(item["top_stocks"]) == 1
    assert item["top_stocks"][0]["code"] == "300750"


def test_sectors_latest_uses_recommendation_trade_date(monkeypatch):
    rec = SimpleNamespace(
        trade_date="2026-04-21",
        sector_name="电池",
        score=35.0,
        bucket="watch",
        reasons_json='["资金净流入"]',
    )
    ai_old = SimpleNamespace(
        trade_date="2026-04-20",
        sector_name="半导体",
        direction="up",
        confidence=8,
        score_up=70,
        score_down=20,
        reasons_json='["旧日期数据"]',
    )
    requested_dates: list[str] = []

    def fake_get_ai_sector_analysis(trade_date: str):
        requested_dates.append(trade_date)
        return []

    monkeypatch.setattr(sectors_route.db, "get_latest_ai_sector_analysis", lambda: [ai_old])
    monkeypatch.setattr(sectors_route.db, "get_ai_sector_analysis", fake_get_ai_sector_analysis)
    monkeypatch.setattr(sectors_route.db, "get_latest_sector_recommendations", lambda: [rec])
    monkeypatch.setattr(sectors_route.db, "get_stock_signals", lambda trade_date: [])
    monkeypatch.setattr(sectors_route.db, "get_latest_stock_signals", lambda limit=500: [])
    monkeypatch.setattr(sectors_route.db, "get_sector_stock_recommendations", lambda trade_date: [])
    monkeypatch.setattr(sectors_route.db, "get_sector_stocks", lambda sector_name, trade_date=None: [])

    app = create_app()
    c = TestClient(app)
    r = c.get("/api/sectors/latest")
    assert r.status_code == 200
    payload = r.json()
    assert payload["trade_date"] == "2026-04-21"
    assert payload["items"][0]["sector_name"] == "电池"
    assert requested_dates == ["2026-04-21"]

