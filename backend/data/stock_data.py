"""
股票数据获取模块
使用 AKShare 统一获取 A 股实时行情和历史数据
"""
from typing import List, Optional, Dict, Any, cast
from datetime import datetime, timedelta
import importlib

from backend.logging_config import logger
from backend.data import akshare_patch
from backend.config import config

akshare_patch.patch()
import akshare as ak
import pandas as pd
import time
import baostock as bs


class StockData:
    """股票数据获取"""

    def __init__(self):
        self._spot_cache = None
        self._spot_cache_time = 0
        self._cache_duration = 60
        self._tushare_pro = None
        self._tushare_ready = False
        self._auction_cache: Dict[str, Dict[str, Any]] = {}

    def _get_spot_data(self) -> pd.DataFrame:
        now = time.time()
        if self._spot_cache is None or (now - self._spot_cache_time) > self._cache_duration:
            logger.info("正在下载行情数据...")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self._spot_cache = ak.stock_zh_a_spot_em()
                    self._spot_cache_time = now
                    logger.info(f"行情数据下载完成，共 {len(self._spot_cache)} 只股票")
                    return self._spot_cache
                except Exception as e:
                    logger.error(f"行情数据下载失败 (尝试 {attempt + 1}/{max_retries}): {e}")
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

    @staticmethod
    def _to_tushare_code(stock_code: str) -> str:
        code = (stock_code or "").strip().upper()
        if not code:
            return ""
        if "." in code:
            return code
        if code.startswith(("6", "9")):
            return f"{code}.SH"
        return f"{code}.SZ"

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or (isinstance(value, str) and not value.strip()):
                return default
            if pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    def _get_tushare_pro(self):
        if self._tushare_ready:
            return self._tushare_pro
        self._tushare_ready = True
        token = (config.TUSHARE_TOKEN or "").strip()
        if not token:
            return None
        try:
            ts = importlib.import_module("tushare")
            ts.set_token(token)
            self._tushare_pro = ts.pro_api(token)
        except Exception as e:
            print(f"[StockData] 初始化 tushare 失败: {e}")
            self._tushare_pro = None
        return self._tushare_pro

    def get_open_auction_snapshot(self, stock_code: str, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取开盘集合竞价快照（stk_auction），用于候选股过滤。

        无 token/无权限/无数据时返回空 dict，调用方应走降级逻辑。
        """
        ts_code = self._to_tushare_code(stock_code)
        if not ts_code:
            return {}

        query_date = (trade_date or "").replace("-", "").strip()
        cache_key = f"{ts_code}:{query_date or 'latest'}"
        if cache_key in self._auction_cache:
            return self._auction_cache[cache_key]

        pro = self._get_tushare_pro()
        if pro is None:
            return {}

        date_candidates = []
        if query_date:
            date_candidates.append(query_date)
        date_candidates.append(datetime.now().strftime("%Y%m%d"))
        date_candidates.append("")

        for day in date_candidates:
            try:
                params: Dict[str, Any] = {"ts_code": ts_code, "limit": 1}
                if day:
                    params["trade_date"] = day
                df = pro.query("stk_auction", **params)
                if df is None or df.empty:
                    continue
                row = df.iloc[0]
                price = self._safe_float(row.get("price"))
                pre_close = self._safe_float(row.get("pre_close"))
                pct_change = ((price - pre_close) / pre_close * 100) if price and pre_close else 0.0
                result = {
                    "has_data": True,
                    "ts_code": ts_code,
                    "trade_date": str(row.get("trade_date", day)),
                    "price": price,
                    "pre_close": pre_close,
                    "pct_change": pct_change,
                    "amount": self._safe_float(row.get("amount")),
                    "volume": self._safe_float(row.get("vol")),
                    "turnover_rate": self._safe_float(row.get("turnover_rate")),
                    "volume_ratio": self._safe_float(row.get("volume_ratio")),
                    "source": "tushare.stk_auction",
                }
                self._auction_cache[cache_key] = result
                return result
            except Exception as e:
                print(f"[StockData] 获取开盘竞价失败 {ts_code}({day or 'latest'}): {e}")
        return {}

    @staticmethod
    def is_open_auction_weak(auction: Dict[str, Any]) -> bool:
        """
        判断竞价是否明显偏弱。

        规则偏保守：只有明显低开且量能弱时才过滤，避免误杀正常候选股。
        """
        if not auction or not auction.get("has_data"):
            return False
        pct_change = float(auction.get("pct_change", 0) or 0)
        volume_ratio = float(auction.get("volume_ratio", 0) or 0)
        amount = float(auction.get("amount", 0) or 0)

        if pct_change <= -3:
            return True
        if pct_change <= -2 and 0 < volume_ratio < 0.6:
            return True
        if pct_change <= -1.5 and amount > 0 and amount < 2_000_000:
            return True
        return False

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
            config_module = importlib.import_module("backend.config")
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

    def get_financial_data(self, stock_code: str, year: int = 2026, quarter: int = 1) -> Dict[str, Any]:
        """
        获取财务数据（净利润、ROE等）

        Args:
            stock_code: 股票代码，如 "600519"
            year: 年份，默认2026
            quarter: 季度(1-4)，默认1

        Returns:
            {
                'has_data': bool,
                'net_profit': float,      # 净利润(元)
                'net_profit_yoy': float,  # 净利润同比(%)
                'roe': float,             # ROE(%)
                'revenue': float,         # 营业收入(元)
            }
        """
        bs_code = self._to_baostock_code(stock_code)
        if not bs_code:
            return {'has_data': False}

        try:
            lg = bs.login()
            if lg.error_code != '0':
                return {'has_data': False}

            rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
            data = []
            while rs.next():
                data.append(rs.get_row_data())

            bs.logout()

            if not data:
                return {'has_data': False}

            df = pd.DataFrame(data, columns=rs.fields)
            row = df.iloc[0]

            net_profit = float(row.get('netProfit', 0) or 0)
            roe = float(row.get('roeAvg', 0) or 0)

            # 对比去年同期计算同比（Q1对Q1，Q2对Q2...）
            yoy = 0.0
            try:
                rs2 = bs.query_profit_data(code=bs_code, year=year-1, quarter=quarter)
                data2 = []
                while rs2.next():
                    data2.append(rs2.get_row_data())
                if data2:
                    df2 = pd.DataFrame(data2, columns=rs2.fields)
                    net_profit_last = float(df2.iloc[0].get('netProfit', 0) or 0)
                    if net_profit_last > 0:
                        yoy = (net_profit - net_profit_last) / net_profit_last * 100
            except:
                pass

            return {
                'has_data': True,
                'net_profit': net_profit,
                'net_profit_yoy': yoy,
                'roe': roe * 100,
                'revenue': float(row.get('MBRevenue', 0) or 0)
            }
        except Exception as e:
            return {'has_data': False}

    def is_stock_has_recent_performance(self, stock_code: str, min_net_profit: float = 1e8,
                                        min_yoy: float = -50.0) -> Dict[str, Any]:
        """
        检查股票是否有近期业绩（用于选股过滤）

        Args:
            stock_code: 股票代码
            min_net_profit: 最小净利润(默认1亿)
            min_yoy: 最小净利润同比(默认-50%)

        Returns:
            {
                'pass': bool,
                'has_financial_data': bool,
                'net_profit': float,
                'net_profit_yoy': float,
                'roe': float,
                'reason': str
            }
        """
        # 优先获取最新季度数据（2026Q1）
        result = self.get_financial_data(stock_code, year=2026, quarter=1)

        if not result.get('has_data'):
            # 尝试2025Q4
            result = self.get_financial_data(stock_code, year=2025, quarter=4)

        if not result.get('has_data'):
            return {
                'pass': False,
                'has_financial_data': False,
                'net_profit': 0,
                'net_profit_yoy': 0,
                'roe': 0,
                'reason': '无财报数据'
            }

        net_profit = result.get('net_profit', 0)
        yoy = result.get('net_profit_yoy', 0)
        roe = result.get('roe', 0)

        # 净利润规模检查
        if net_profit < min_net_profit:
            return {
                'pass': False,
                'has_financial_data': True,
                'net_profit': net_profit,
                'net_profit_yoy': yoy,
                'roe': roe,
                'reason': f'净利润不足{int(net_profit/1e8)}亿'
            }

        # 净利润同比检查
        if yoy < min_yoy:
            return {
                'pass': False,
                'has_financial_data': True,
                'net_profit': net_profit,
                'net_profit_yoy': yoy,
                'roe': roe,
                'reason': f'净利润同比{yoy:.1f}%下降'
            }

        return {
            'pass': True,
            'has_financial_data': True,
            'net_profit': net_profit,
            'net_profit_yoy': yoy,
            'roe': roe,
            'reason': '业绩达标'
        }

    @staticmethod
    def _to_baostock_code(stock_code: str) -> str:
        """转换为baostock格式"""
        code = (stock_code or "").strip()
        if not code:
            return ""
        if code.startswith("sh.") or code.startswith("sz."):
            return code
        if code.startswith(("6", "9")):
            return f"sh.{code}"
        return f"sz.{code}"


stock_data = StockData()
