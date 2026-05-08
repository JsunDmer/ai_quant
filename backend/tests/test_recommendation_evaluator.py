import json
from types import SimpleNamespace

import pandas as pd

from backend.data.db import RecommendationEvaluation
from backend.evaluation.recommendation_evaluator import RecommendationEvaluator


def test_evaluate_for_date_writes_recommendation_rows(monkeypatch):
    evaluator = RecommendationEvaluator()
    saved_rows = []

    monkeypatch.setattr(
        evaluator._db,
        "get_stock_signals",
        lambda trade_date: [
            SimpleNamespace(
                signal="buy",
                stock_code="000001",
                stock_name="平安银行",
                sector_name="银行",
            )
        ],
    )
    monkeypatch.setattr(evaluator._db, "get_sector_stock_recommendations", lambda trade_date: [])
    monkeypatch.setattr(
        evaluator._db,
        "get_next_n_trading_dates",
        lambda from_date, n: ["2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19", "2024-01-22"][:n],
    )
    monkeypatch.setattr(
        evaluator._db,
        "get_sector_daily_performance",
        lambda trade_date: [SimpleNamespace(sector_name="银行", change_pct=1.0)],
    )
    monkeypatch.setattr(
        evaluator._db,
        "batch_upsert_recommendation_evaluations",
        lambda rows: saved_rows.extend(rows) or True,
    )

    kline_df = pd.DataFrame(
        {
            "date": ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19", "2024-01-22"],
            "close": [10.0, 10.1, 10.3, 10.4, 10.6, 10.8],
        }
    )
    monkeypatch.setattr(evaluator._stock_data, "get_kline_data", lambda stock_code, days=260: kline_df.copy())

    count = evaluator.evaluate_for_date("2024-01-15")
    assert count == 1
    assert len(saved_rows) == 1
    row = saved_rows[0]
    assert row.stock_code == "000001"
    assert row.recommendation_type == "stock_signal"
    assert row.return_1d is not None
    assert row.return_3d is not None
    assert row.return_5d is not None


def test_get_summary_metrics():
    evaluator = RecommendationEvaluator()
    rows = [
        RecommendationEvaluation(
            recommendation_date="2024-01-15",
            recommendation_type="stock_signal",
            source="signal",
            stock_code="000001",
            return_1d=1.0,
            return_3d=2.0,
            return_5d=3.0,
            excess_return_1d=0.2,
            excess_return_3d=0.5,
            excess_return_5d=0.8,
        ),
        RecommendationEvaluation(
            recommendation_date="2024-01-15",
            recommendation_type="stock_signal",
            source="signal",
            stock_code="000002",
            return_1d=-0.5,
            return_3d=1.0,
            return_5d=None,
            excess_return_1d=-0.1,
            excess_return_3d=0.2,
            excess_return_5d=None,
        ),
    ]

    evaluator._load_rows = lambda **kwargs: rows  # type: ignore[method-assign]
    evaluator._compute_index_forward_return = lambda index_code, recommendation_date, horizon_days: 0.5  # type: ignore[method-assign]
    evaluator._compute_simple_momentum_baseline = lambda recommendation_date, horizon_days: 0.8  # type: ignore[method-assign]

    summary = evaluator.get_summary()
    assert summary["total_recommendations"] == 2
    assert summary["t1"]["evaluated_count"] == 2
    assert summary["t1"]["hit_count"] == 1
    assert summary["t1"]["hit_rate"] == 50.0
    assert summary["t5"]["evaluated_count"] == 1
    assert summary["t1"]["avg_baseline_hs300_return"] == 0.5
    assert summary["t1"]["avg_baseline_momentum_return"] == 0.8
    assert "avg_excess_return_sector" in summary["t1"]


def test_compute_index_forward_return_from_snapshot(monkeypatch):
    evaluator = RecommendationEvaluator()
    monkeypatch.setattr(
        evaluator._db,
        "get_next_n_trading_dates",
        lambda from_date, n: ["2024-01-16", "2024-01-17", "2024-01-18"][:n],
    )

    snapshots = {
        "2024-01-16": SimpleNamespace(indices_json=json.dumps([{"code": "000300", "change": 1.0}])),
        "2024-01-17": SimpleNamespace(indices_json=json.dumps([{"code": "000300", "change": -0.5}])),
        "2024-01-18": SimpleNamespace(indices_json=json.dumps([{"code": "000300", "change": 2.0}])),
    }
    monkeypatch.setattr(evaluator._db, "get_market_snapshot", lambda date: snapshots.get(date))

    value = evaluator._compute_index_forward_return("000300", "2024-01-15", 3)
    assert value is not None
    assert round(value, 4) == 2.5049
