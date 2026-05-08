from types import SimpleNamespace

from backend.evaluation.portfolio_builder import PortfolioBuilder


def test_portfolio_builder_handles_empty():
    builder = PortfolioBuilder()
    builder._load_signals = lambda trade_date=None: ("", [])  # type: ignore[method-assign]
    result = builder.suggest()
    assert result["summary"]["selected_count"] == 0
    assert result["summary"]["cash_weight"] == 1.0


def test_portfolio_builder_respects_caps():
    builder = PortfolioBuilder()
    rows = [
        SimpleNamespace(
            trade_date="2024-01-15",
            stock_code="000001",
            stock_name="平安银行",
            sector_name="银行",
            signal="strong_buy",
            confidence=0.88,
        ),
        SimpleNamespace(
            trade_date="2024-01-15",
            stock_code="000002",
            stock_name="万科A",
            sector_name="地产",
            signal="buy",
            confidence=0.72,
        ),
        SimpleNamespace(
            trade_date="2024-01-15",
            stock_code="000003",
            stock_name="国联证券",
            sector_name="券商",
            signal="buy",
            confidence=0.7,
        ),
        SimpleNamespace(
            trade_date="2024-01-15",
            stock_code="000004",
            stock_name="白酒A",
            sector_name="白酒",
            signal="buy",
            confidence=0.68,
        ),
    ]
    builder._load_signals = lambda trade_date=None: ("2024-01-15", rows)  # type: ignore[method-assign]
    result = builder.suggest(top_n=4, max_single_weight=0.35, max_sector_weight=0.5)
    assert result["summary"]["selected_count"] > 0
    assert result["summary"]["max_single_weight_actual"] <= 0.351
    assert result["summary"]["max_sector_weight_actual"] <= 0.501
