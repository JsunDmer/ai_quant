import importlib


def test_kline_fallback_order(monkeypatch):
    stock_data = importlib.import_module("data.stock_data")
    sd = stock_data.StockData()
    calls = []

    def fail_first(*args, **kwargs):
        calls.append("akshare")
        raise RuntimeError("fail")

    def succeed_second(*args, **kwargs):
        calls.append("efinance")
        return sd._normalize_kline_df(sd._fake_kline_df())

    monkeypatch.setattr(sd, "_fetch_kline_akshare", fail_first)
    monkeypatch.setattr(sd, "_fetch_kline_efinance", succeed_second)

    df = sd.get_kline_data("600519", days=10)
    assert not df.empty
    assert calls == ["akshare", "efinance"]
