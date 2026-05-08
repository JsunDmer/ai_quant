import pandas as pd

from backend import pipeline as pipeline_mod
from backend.pipeline import run_post_close_pipeline


def test_dashboard_report_shape():
    result = run_post_close_pipeline(ai_enabled=False, refresh_realtime_only=True)
    report = result.get("dashboard_report")
    assert report is not None
    assert "headline" in report
    assert "summary" in report


def test_pipeline_diagnostics_counts_candidate_and_signal_steps(monkeypatch):
    class FakeSectorData:
        def recommend_sectors(self):
            return {
                "strong_recommend": [
                    {"sector_name": "半导体", "score": 45, "bucket": "strong_recommend", "reasons": []}
                ],
                "watch": [],
                "hold": [],
            }

        def recommend_stocks_for_sector(self, sector_name, trade_date=None, min_count=3, max_count=5, allow_history=True):
            return [
                {"code": "688001", "name": "股票A", "price": 10.0, "change": 3.2},
                {"code": "688002", "name": "股票B", "price": 11.0, "change": 1.2},
            ]

    class FakeStockData:
        def get_open_auction_snapshot(self, code, trade_date=None):
            return {"has_data": False}

        def is_open_auction_weak(self, auction):
            return False

        def get_kline_data(self, code, days):
            return pd.DataFrame(
                {
                    "open": [10.0] * 20,
                    "close": [10.0] * 20,
                    "high": [10.0] * 20,
                    "low": [10.0] * 20,
                    "volume": [1000] * 20,
                }
            )

    class FakeStrategy:
        def analyze_stock(self, code, kline):
            if code == "688001":
                return {"signal": "strong_buy", "confidence": 0.8, "factors": []}
            return {"signal": "hold", "confidence": 0.3, "factors": []}

    class FakeDatabase:
        def upsert_market_snapshot(self, snapshot):
            return True

        def upsert_sector_recommendation(self, rec):
            return True

        def upsert_stock_signal(self, signal):
            return True

    monkeypatch.setattr(pipeline_mod, "SectorData", FakeSectorData)
    monkeypatch.setattr(pipeline_mod, "StockData", FakeStockData)
    monkeypatch.setattr(pipeline_mod, "QuantStrategy", FakeStrategy)
    monkeypatch.setattr(pipeline_mod, "Database", FakeDatabase)

    result = run_post_close_pipeline(
        trade_date="2026-04-21",
        ai_enabled=False,
        refresh_realtime_only=True,
    )

    diagnostics = result["diagnostics"]
    assert set(diagnostics) >= {
        "market_snapshot",
        "sector_scoring",
        "candidate_pick",
        "signal_generation",
    }
    assert diagnostics["sector_scoring"]["recommendation_count"] == 1
    assert diagnostics["candidate_pick"]["selected_sector_count"] == 1
    assert diagnostics["candidate_pick"]["candidate_count_before_auction"] == 2
    assert diagnostics["candidate_pick"]["candidate_count_after_auction"] == 2
    assert diagnostics["signal_generation"]["candidates_input"] == 2
    assert diagnostics["signal_generation"]["kline_success_count"] == 2
    assert diagnostics["signal_generation"]["signal_counts"]["strong_buy"] == 1
    assert diagnostics["signal_generation"]["signal_counts"]["hold"] == 1
    assert diagnostics["signal_generation"]["buy_signal_count"] == 1
