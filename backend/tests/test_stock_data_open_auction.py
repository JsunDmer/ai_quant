from backend.data.stock_data import StockData


def test_to_tushare_code_conversion():
    assert StockData._to_tushare_code("600000") == "600000.SH"
    assert StockData._to_tushare_code("000001") == "000001.SZ"
    assert StockData._to_tushare_code("300750") == "300750.SZ"
    assert StockData._to_tushare_code("600519.SH") == "600519.SH"


def test_open_auction_weak_detection():
    assert StockData.is_open_auction_weak({"has_data": True, "pct_change": -3.1, "volume_ratio": 1.0, "amount": 5_000_000})
    assert StockData.is_open_auction_weak({"has_data": True, "pct_change": -2.1, "volume_ratio": 0.5, "amount": 8_000_000})
    assert StockData.is_open_auction_weak({"has_data": True, "pct_change": -1.8, "volume_ratio": 0.9, "amount": 1_000_000})


def test_open_auction_keep_when_not_weak():
    assert not StockData.is_open_auction_weak({})
    assert not StockData.is_open_auction_weak({"has_data": False, "pct_change": -4.0})
    assert not StockData.is_open_auction_weak({"has_data": True, "pct_change": -0.8, "volume_ratio": 0.3, "amount": 500_000})
    assert not StockData.is_open_auction_weak({"has_data": True, "pct_change": 1.2, "volume_ratio": 1.1, "amount": 3_000_000})
