from pipeline import get_trading_date


def test_non_trading_day_rolls_back():
    trade_date, data_date = get_trading_date("2024-10-01")
    assert trade_date < data_date
