from backend.data.sector_data import SectorData


def test_recommend_stocks_prefers_positive_then_fallback(monkeypatch):
    sd = SectorData()
    stocks = [
        {"code": "0001", "name": "A", "price": 10.2, "change": 2.4},
        {"code": "0002", "name": "B", "price": 8.5, "change": -1.2},
        {"code": "0003", "name": "C", "price": 12.0, "change": 3.8},
        {"code": "0004", "name": "D", "price": 0, "change": 5.2},
        {"code": "0005", "name": "E", "price": 6.1, "change": 1.1},
    ]
    monkeypatch.setattr(sd, "get_sector_stocks", lambda sector_name, trade_date=None: stocks)

    picks = sd.recommend_stocks_for_sector(
        sector_name="电池",
        trade_date="2026-04-21",
        min_count=3,
        max_count=4,
        allow_history=False,
    )

    assert [p["code"] for p in picks] == ["0003", "0001", "0005", "0002"]
    assert picks[0]["reason"].startswith("板块内领涨")
    assert picks[-1]["reason"].startswith("板块内相对抗跌")


def test_recommend_stocks_fallback_to_history_cache(monkeypatch):
    sd = SectorData()
    monkeypatch.setattr(sd, "get_sector_stocks", lambda sector_name, trade_date=None: [])
    monkeypatch.setattr(
        sd,
        "get_sector_stocks_with_history",
        lambda sector_name: [
            {"code": "0006", "name": "F", "price": 10.0, "change": 0.0},
            {"code": "0007", "name": "G", "price": 9.8, "change": -0.8},
            {"code": "0008", "name": "H", "price": 11.3, "change": -2.1},
            {"code": "0009", "name": "I", "price": 0.0, "change": 4.0},
        ],
    )

    picks = sd.recommend_stocks_for_sector(
        sector_name="贵金属",
        trade_date="2026-04-21",
        min_count=3,
        max_count=3,
        allow_history=True,
    )

    assert [p["code"] for p in picks] == ["0006", "0007", "0008"]
    assert picks[0]["reason"] == "板块内相对稳健"
    assert picks[1]["reason"].startswith("板块内相对抗跌")
