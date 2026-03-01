import importlib

import pandas as pd


def test_normalize_kline_columns():
    df = pd.DataFrame(
        {
            "日期": ["2024-01-01"],
            "开盘": [10],
            "收盘": [12],
            "最高": [13],
            "最低": [9],
            "成交量": [1000],
            "成交额": [10000],
            "涨跌幅": [1.2],
        }
    )
    stock_data = importlib.import_module("data.stock_data")
    normalized = stock_data.StockData()._normalize_kline_df(df)
    assert {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "pct_chg",
    }.issubset(normalized.columns)
