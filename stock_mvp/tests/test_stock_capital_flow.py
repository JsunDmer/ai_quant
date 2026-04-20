import pytest
from stock_mvp.data.stock_data import StockData


def test_get_stock_capital_flow():
    """测试获取个股资金流向"""
    stock = StockData()
    # 测试常用股票
    result = stock.get_stock_capital_flow("600519")  # 茅台
    assert isinstance(result, dict)
    assert 'main_inflow' in result
    assert 'main_inflow_pct' in result
    print(f"茅台资金流向: {result}")


def test_get_stock_capital_flow_empty():
    """测试获取不存在股票的资金流向"""
    stock = StockData()
    result = stock.get_stock_capital_flow("999999")
    assert result['main_inflow'] == 0