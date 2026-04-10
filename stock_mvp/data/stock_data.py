"""
股票数据获取模块
使用 AKShare 统一获取 A 股实时行情和历史数据
"""
from typing import List, Optional, Dict, Any, cast
from datetime import datetime, timedelta
import importlib
import akshare as ak
import pandas as pd
import time


class StockData:
    """股票数据获取"""

    def __init__(self):
        self._spot_cache = None
        self._spot_cache_time = 0
        self._cache_duration = 60

    def _get_spot_data(self) -> pd.DataFrame:
        now = time.time()
        if self._spot_cache is None or (now - self._spot_cache_time) > self._cache_duration:
            print("[StockData] 正在下载行情数据...")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self._spot_cache = ak.stock_zh_a_spot_em()
                    self._spot_cache_time = now
                    print(f"[StockData] 行情数据下载完成，共 {len(self._spot_cache)} 只股票")
                    return self._spot_cache
                except Exception as e:
                    print(f"[StockData] 行情数据下载失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
            print("[StockData] 行情数据下载失败，返回空数据")
            return pd.DataFrame()
        return self._spot_cache
    
    def search_stock(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索股票"""
        try:
            df = self._get_spot_data()
            
            # 精确匹配股票代码
            exact = df[df['代码'] == keyword]
            if not exact.empty:
                exact_records = pd.DataFrame(exact.loc[:, ['代码', '名称']])
                return exact_records.to_dict(orient="records")
            
            # 模糊匹配名称
            result = df[df['名称'].str.contains(keyword, na=False)].head(20)
            result_records = pd.DataFrame(result.loc[:, ['代码', '名称']])
            return result_records.to_dict(orient="records")
        except Exception as e:
            print(f"搜索股票失败: {e}")
            return []
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取实时行情"""
        try:
            print(f"[StockData] 获取实时行情 {stock_code} ...")
            df = self._get_spot_data()
            stock = df[df['代码'] == stock_code]
            if stock.empty:
                return None
            
            row = stock.iloc[0]
            result = {
                'code': row['代码'],
                'name': row['名称'],
                'price': float(row['最新价']),
                'open': float(row['今开']),
                'high': float(row['最高']),
                'low': float(row['最低']),
                'pre_close': float(row['昨收']),
                'volume': int(row['成交量']),
                'amount': float(row['成交额']),
                'change_percent': float(row['涨跌幅']),
                'change_amount': float(row['涨跌额']),
                'turnover_rate': float(row.get('换手率', 0)),
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            print(f"[StockData] 获取实时行情 {stock_code} 完成，价: {result['price']:.2f}")
            return result
        except Exception as e:
            print(f"[StockData] 获取实时行情 {stock_code} 失败: {e}")
            return None
    
    def get_batch_quotes(self, stock_codes: List[str]) -> List[Dict[str, Any]]:
        """批量获取实时行情"""
        try:
            df = self._get_spot_data()
            result = []
            for code in stock_codes:
                stock = df[df['代码'] == code]
                if not stock.empty:
                    row = stock.iloc[0]
                    result.append({
                        'code': row['代码'],
                        'name': row['名称'],
                        'price': float(row['最新价']),
                        'pre_close': float(row['昨收']),
                        'change_percent': float(row['涨跌幅']),
                        'change_amount': float(row['涨跌额']),
                    })
            return result
        except Exception as e:
            print(f"批量获取行情失败: {e}")
            return []

    def _normalize_kline_df(self, df: pd.DataFrame) -> pd.DataFrame:
        column_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "涨跌幅": "pct_chg",
            "涨跌额": "change_amount",
            "换手率": "turnover_rate",
        }
        renamed = df.rename(columns=column_map)
        required = ["date", "open", "high", "low", "close", "volume", "amount", "pct_chg"]
        for name in required:
            if name not in renamed.columns:
                renamed[name] = pd.NA
        normalized = renamed.copy()
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
        for col in ["open", "high", "low", "close", "volume", "amount", "pct_chg"]:
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce")
        normalized = normalized.sort_values("date").reset_index(drop=True)
        return normalized

    def _fake_kline_df(self) -> pd.DataFrame:
        return pd.DataFrame(
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

    def _fetch_kline_akshare(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )

    def _fetch_kline_efinance(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            ef = importlib.import_module("efinance")
        except Exception as exc:
            raise RuntimeError("efinance not available") from exc
        df = ef.stock.get_quote_history(stock_code, beg=start_date, end=end_date)
        return pd.DataFrame(df)

    def _fetch_kline_tushare(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            ts = importlib.import_module("tushare")
        except Exception as exc:
            raise RuntimeError("tushare not available") from exc
        pro = ts.pro_api()
        df = pro.daily(ts_code=stock_code, start_date=start_date, end_date=end_date)
        return pd.DataFrame(df)
    
    def get_kline_data(self, stock_code: str, days: int = 60) -> pd.DataFrame:
        """获取 K 线数据"""
        try:
            print(f"[StockData] 获取K线数据 {stock_code} ...")
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            config_module = importlib.import_module("config")
            priority = [
                item.strip()
                for item in config_module.Config().DATA_SOURCE_PRIORITY.split(",")
                if item.strip()
            ]
            fetchers = {
                "akshare": self._fetch_kline_akshare,
                "efinance": self._fetch_kline_efinance,
                "tushare": self._fetch_kline_tushare,
            }
            for source in priority:
                fetcher = fetchers.get(source)
                if fetcher is None:
                    continue
                try:
                    df = fetcher(stock_code, start_date, end_date)
                except Exception:
                    continue
                if df.empty:
                    continue
                result_df = self._normalize_kline_df(df)
                print(f"[StockData] 获取K线数据 {stock_code} 完成，共 {len(result_df)} 条")
                return result_df
            print(f"[StockData] 获取K线数据 {stock_code} 失败: 所有数据源均无数据")
            return pd.DataFrame()
        except Exception as e:
            print(f"[StockData] 获取K线数据 {stock_code} 失败: {e}")
            return pd.DataFrame()
    
    def get_stock_news(self, stock_code: str, limit: int = 10) -> List[Dict[str, str]]:
        """获取股票相关新闻"""
        try:
            df = ak.stock_news_em(symbol=stock_code)
            if df.empty:
                return []
            
            news_list = []
            for _, row in df.head(limit).iterrows():
                news_list.append({
                    'title': row['新闻标题'],
                    'content': row['新闻内容'],
                    'time': row['发布时间'],
                    'source': row.get('新闻来源', '')
                })
            return news_list
        except Exception as e:
            print(f"获取股票新闻失败: {e}")
            return []
    
    def get_market_news(self, limit: int = 20) -> List[Dict[str, str]]:
        """获取市场快讯"""
        try:
            df = ak.stock_news_em(symbol="财经新闻")
            if df.empty:
                return []
            
            news_list = []
            for _, row in df.head(limit).iterrows():
                news_list.append({
                    'title': row['新闻标题'],
                    'content': row['新闻内容'],
                    'time': row['发布时间'],
                })
            return news_list
        except Exception as e:
            print(f"获取市场新闻失败: {e}")
            return []

    def get_stock_capital_flow(self, stock_code: str) -> Dict[str, Any]:
        """
        获取个股大资金流向（单日）

        Args:
            stock_code: 股票代码，如 "600519"

        Returns:
            {
                'main_inflow': float,    # 主力净流入(万元)
                'main_inflow_pct': float, # 主力净流入占比(%)
                'super_inflow': float,    # 超大单净流入(万元)
                'large_inflow': float,    # 大单净流入(万元)
                'medium_inflow': float,   # 中单净流入(万元)
                'small_inflow': float,    # 小单净流入(万元)
                'trade_date': str         # 交易日期
            }
        """
        try:
            # 确定市场代码
            market = "sh" if stock_code.startswith("6") else "sz"
            
            # 使用 akshare 的个股资金流向接口
            # API: ak.stock_individual_fund_flow(stock="600519", market="sh")
            df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
            
            if df is None or df.empty:
                print(f"[StockData] 资金流向 {stock_code} 无数据")
                return self._empty_capital_flow()
            
            latest = df.iloc[0]
            result = {
                'main_inflow': float(latest.get('主力净流入-净额', 0)) if pd.notna(latest.get('主力净流入-净额')) else 0,
                'main_inflow_pct': float(latest.get('主力净流入-净占比', 0)) if pd.notna(latest.get('主力净流入-净占比')) else 0,
                'super_inflow': float(latest.get('超大单净流入-净额', 0)) if pd.notna(latest.get('超大单净流入-净额')) else 0,
                'large_inflow': float(latest.get('大单净流入-净额', 0)) if pd.notna(latest.get('大单净流入-净额')) else 0,
                'medium_inflow': float(latest.get('中单净流入-净额', 0)) if pd.notna(latest.get('中单净流入-净额')) else 0,
                'small_inflow': float(latest.get('小单净流入-净额', 0)) if pd.notna(latest.get('小单净流入-净额')) else 0,
                'trade_date': str(latest.get('日期', ''))
            }
            print(f"[StockData] 资金流向 {stock_code}，主力净流入: {result['main_inflow']:.2f}万")
            return result
        except Exception as e:
            print(f"[StockData] 获取个股资金流向失败 {stock_code}: {e}")
            return self._empty_capital_flow()

    def _empty_capital_flow(self) -> Dict[str, Any]:
        """返回空资金流向数据"""
        return {
            'main_inflow': 0, 'main_inflow_pct': 0,
            'super_inflow': 0, 'large_inflow': 0,
            'medium_inflow': 0, 'small_inflow': 0,
            'trade_date': ''
        }


stock_data = StockData()
