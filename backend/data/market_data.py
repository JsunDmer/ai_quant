"""
市场数据模块 - 收盘后快照采集
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import importlib
import pandas as pd

from backend.logging_config import logger
from backend.data import akshare_patch
from backend.config import config

akshare_patch.patch()
import akshare as ak
import time


class MarketData:
    """市场数据采集"""
    
    def __init__(self):
        self._spot_cache = None
        self._spot_cache_time = 0
        self._cache_duration = 60
        self._tushare_module = None
        self._tushare_pro = None
        self._tushare_ready = False
        self._north_flow_cache: Dict[str, Any] = {"data": {'north': 0, 'south': 0}, "ts": 0.0}
        self._north_flow_cache_duration = 120
        self._movers_cache: Dict[str, Any] = {"key": "", "data": [], "ts": 0.0}
        self._movers_cache_duration = 45
    
    def _get_spot_data(self) -> pd.DataFrame:
        now = time.time()
        if self._spot_cache is None or (now - self._spot_cache_time) > self._cache_duration:
            try:
                self._spot_cache = ak.stock_zh_a_spot_em()
            except Exception:
                try:
                    self._spot_cache = ak.stock_zh_a_spot()
                except Exception as e:
                    print(f"[MarketData] 获取实时行情失败: {e}")
                    self._spot_cache = pd.DataFrame()
            self._spot_cache_time = now
        return self._spot_cache

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

    def _get_tushare_module_and_pro(self):
        if self._tushare_ready:
            return self._tushare_module, self._tushare_pro
        self._tushare_ready = True
        token = (config.TUSHARE_TOKEN or "").strip()
        if not token:
            return None, None
        try:
            ts = importlib.import_module("tushare")
            ts.set_token(token)
            self._tushare_module = ts
            self._tushare_pro = ts.pro_api(token)
        except Exception as e:
            print(f"[MarketData] 初始化 tushare 失败: {e}")
            self._tushare_module = None
            self._tushare_pro = None
        return self._tushare_module, self._tushare_pro
    
    def get_indices(self) -> List[Dict[str, Any]]:
        try:
            df = ak.stock_zh_index_spot_sina()
            indices = []
            for code in ['sh000001', 'sz399001', 'sz399006', 'sh000688', 'sh000300', 'sh000905', 'sh000852']:
                row = df[df['代码'] == code]
                if not row.empty:
                    r = row.iloc[0]
                    indices.append({
                        'code': code.replace('sh', '').replace('sz', ''),
                        'name': r['名称'],
                        'price': float(r['最新价']) if pd.notna(r['最新价']) else 0,
                        'change': float(r['涨跌幅']) if pd.notna(r['涨跌幅']) else 0
                    })
            print(f"[MarketData] 获取指数完成，共 {len(indices)} 个")
            return indices
        except Exception as e:
            print(f"[MarketData] 获取指数失败: {e}")
            return []
    
    def get_market_breadth(self) -> Dict[str, Any]:
        """获取涨跌分布"""
        try:
            df = self._get_spot_data()
            total = len(df)
            up_count = len(df[df['涨跌幅'] > 0])
            down_count = len(df[df['涨跌幅'] < 0])
            flat_count = total - up_count - down_count
            limit_up = len(df[df['涨跌幅'] >= 9.9]) if '涨跌幅' in df.columns else 0
            limit_down = len(df[df['涨跌幅'] <= -9.9]) if '涨跌幅' in df.columns else 0
            
            result = {
                'total': total,
                'up': up_count,
                'down': down_count,
                'flat': flat_count,
                'limit_up': limit_up,
                'limit_down': limit_down
            }
            print(f"[MarketData] 涨跌分布: 涨 {up_count} / 跌 {down_count} / 平 {flat_count}")
            return result
        except Exception as e:
            print(f"[MarketData] 获取涨跌分布失败: {e}")
            return {'total': 0, 'up': 0, 'down': 0, 'flat': 0, 'limit_up': 0, 'limit_down': 0}
    
    def get_turnover(self) -> Dict[str, Any]:
        """获取成交额"""
        try:
            df = self._get_spot_data()
            total_amount = df['成交额'].sum() if '成交额' in df.columns else 0
            total_volume = df['成交量'].sum() if '成交量' in df.columns else 0
            result = {
                'amount': float(total_amount) if pd.notna(total_amount) else 0,
                'volume': int(total_volume) if pd.notna(total_volume) else 0
            }
            print(f"[MarketData] 成交额: {result['amount']/100000000:.2f}亿")
            return result
        except Exception as e:
            print(f"[MarketData] 获取成交额失败: {e}")
            return {'amount': 0, 'volume': 0}
    
    def get_north_flow(self) -> Dict[str, Any]:
        """获取北向资金"""
        now = time.time()
        if (now - self._north_flow_cache.get("ts", 0)) <= self._north_flow_cache_duration:
            return self._north_flow_cache.get("data", {'north': 0, 'south': 0})

        _, pro = self._get_tushare_module_and_pro()
        if pro is None:
            return {'north': 0, 'south': 0, 'trade_date': '', 'source': 'fallback'}

        today = datetime.now().strftime('%Y%m%d')
        week_ago = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        param_candidates = [
            {'trade_date': today},
            {'start_date': week_ago, 'end_date': today, 'limit': 1},
            {'limit': 1},
        ]
        for params in param_candidates:
            try:
                df = pro.query('moneyflow_hsgt', **params)
                if df is None or df.empty:
                    continue
                row = df.iloc[0]
                north = self._safe_float(row.get('north_money'))
                south = self._safe_float(row.get('south_money'))
                result = {
                    'north': north,
                    'south': south,
                    'north_money': north,
                    'south_money': south,
                    'trade_date': str(row.get('trade_date', '')),
                    'source': 'tushare.moneyflow_hsgt',
                }
                self._north_flow_cache = {"data": result, "ts": now}
                return result
            except Exception as e:
                print(f"[MarketData] 获取北向资金失败 ({params}): {e}")

        return {'north': 0, 'south': 0, 'trade_date': '', 'source': 'fallback'}

    def get_realtime_movers(self, stock_codes: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        基于关注池获取实时异动榜（按涨跌幅绝对值排序）

        注意：这里使用 realtime_quote 获取关注池实时价格，避免 realtime_list 全市场抓取过慢。
        """
        ts_module, _ = self._get_tushare_module_and_pro()
        if ts_module is None:
            return []

        normalized_codes: List[str] = []
        seen = set()
        for code in stock_codes or []:
            ts_code = self._to_tushare_code(str(code))
            if not ts_code or ts_code in seen:
                continue
            seen.add(ts_code)
            normalized_codes.append(ts_code)
            if len(normalized_codes) >= 200:
                break

        if not normalized_codes:
            return []

        cache_key = ",".join(normalized_codes)
        now = time.time()
        if (
            self._movers_cache.get("key") == cache_key
            and (now - self._movers_cache.get("ts", 0)) <= self._movers_cache_duration
        ):
            return self._movers_cache.get("data", [])[:limit]

        try:
            df = ts_module.realtime_quote(ts_code=cache_key)
            if df is None or df.empty:
                return []
            movers: List[Dict[str, Any]] = []
            for _, row in df.iterrows():
                ts_code = str(row.get('TS_CODE', '')).strip()
                name = str(row.get('NAME', '')).strip()
                price = self._safe_float(row.get('PRICE'))
                pre_close = self._safe_float(row.get('PRE_CLOSE'))
                pct_change = self._safe_float(row.get('PCT_CHANGE'))
                if pct_change == 0 and price and pre_close:
                    pct_change = (price - pre_close) / pre_close * 100
                movers.append(
                    {
                        'ts_code': ts_code,
                        'name': name,
                        'price': price,
                        'pre_close': pre_close,
                        'pct_change': pct_change,
                        'change': self._safe_float(row.get('CHANGE')),
                        'volume': self._safe_float(row.get('VOLUME')),
                        'amount': self._safe_float(row.get('AMOUNT')),
                        'time': str(row.get('TIME', '')),
                    }
                )
            movers.sort(key=lambda x: abs(self._safe_float(x.get('pct_change'))), reverse=True)
            ranked = movers[: max(limit, 1)]
            self._movers_cache = {"key": cache_key, "data": ranked, "ts": now}
            return ranked
        except Exception as e:
            print(f"[MarketData] 获取实时异动榜失败: {e}")
            return []
    
    def get_news(self, limit: int = 10, enabled_sources: list = None) -> List[Dict[str, str]]:
        """获取财经新闻（多源采集，akshare 兜底）"""
        # 优先使用多源采集器
        try:
            from backend.data.news_collector import collect_all_news
            news = collect_all_news(limit=limit, enabled_sources=enabled_sources)
            if news:
                return news
            print("[MarketData] 多源采集返回空结果，尝试 akshare 兜底")
        except Exception as e:
            print(f"[MarketData] 多源采集失败: {e}")

        # 兜底: akshare
        try:
            df = ak.stock_news_em(symbol="财经新闻")
            if df.empty:
                return []
            news = []
            for _, row in df.head(limit).iterrows():
                news.append({
                    'title': str(row.get('新闻标题', ''))[:100],
                    'content': str(row.get('新闻内容', ''))[:500],
                    'time': str(row.get('发布时间', '')),
                    'source': str(row.get('文章来源', '')),
                    'url': str(row.get('新闻链接', '')),
                })
            return news
        except Exception as e:
            print(f"[MarketData] akshare兜底失败: {e}")
            return []
    
    def collect_post_close_snapshot(self, trade_date: Optional[str] = None, enabled_sources: list = None) -> Dict[str, Any]:
        """
        采集收盘后市场快照
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        print("[MarketData] 开始采集市场快照...")
        
        result = {
            'trade_date': trade_date,
            'status': 'ok',
            'indices': [],
            'market_breadth': {},
            'turnover': {},
            'north_flow': {},
            'news': []
        }
        
        # 采集各类数据
        try:
            result['indices'] = self.get_indices()
            print("[MarketData] 指数采集完成")
        except Exception as e:
            result['indices'] = []
            print(f"[MarketData] 指数采集失败: {e}")
        
        try:
            result['market_breadth'] = self.get_market_breadth()
            print("[MarketData] 涨跌分布采集完成")
        except Exception as e:
            result['market_breadth'] = {}
            print(f"[MarketData] 涨跌分布采集失败: {e}")
        
        try:
            result['turnover'] = self.get_turnover()
            print("[MarketData] 成交额采集完成")
        except Exception as e:
            result['turnover'] = {}
            print(f"[MarketData] 成交额采集失败: {e}")
        
        try:
            result['north_flow'] = self.get_north_flow()
            print("[MarketData] 北向资金采集完成")
        except Exception as e:
            result['north_flow'] = {}
            print(f"[MarketData] 北向资金采集失败: {e}")
        
        try:
            result['news'] = self.get_news(enabled_sources=enabled_sources)
            print("[MarketData] 快讯采集完成")
        except Exception as e:
            result['news'] = []
            print(f"[MarketData] 快讯采集失败: {e}")
        
        # 检查是否需要降级
        if not result['indices'] and not result['market_breadth']:
            result['status'] = 'degraded'
        
        return result


market_data = MarketData()



class InternationalDataCollector:
    """国际市场的数据采集"""
    
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = 60  # 1分钟缓存
    
    def _get_cached(self, key: str, fetch_func):
        """获取缓存数据"""
        now = time.time()
        if key not in self._cache or (now - self._cache_time.get(key, 0)) > self._cache_duration:
            self._cache[key] = fetch_func()
            self._cache_time[key] = now
        return self._cache[key]
    
    def get_us_indices(self) -> Dict[str, Any]:
        """获取美国主要股指"""
        try:
            indices_map = {
                '.DJI': 'dow_jones',
                '.IXIC': 'nasdaq',
                '.INX': 'sp500'
            }
            result = {}
            for symbol, name in indices_map.items():
                try:
                    df = ak.index_us_stock_sina(symbol)
                    if not df.empty:
                        latest = df.iloc[-1]
                        price = float(latest.get('最新价', 0)) if pd.notna(latest.get('最新价')) else 0
                        change_pct = float(latest.get('涨跌幅', 0)) if pd.notna(latest.get('涨跌幅')) else 0
                        result[name] = {
                            'price': price,
                            'change_pct': change_pct
                        }
                except Exception as e:
                    print(f"[MarketData] 获取{name}失败: {e}")
                    result[name] = {'price': 0, 'change_pct': 0}
            return result
        except Exception as e:
            print(f"[MarketData] 获取US indices失败: {e}")
            return {'dow_jones': {'price': 0, 'change_pct': 0}, 'nasdaq': {'price': 0, 'change_pct': 0}, 'sp500': {'price': 0, 'change_pct': 0}}
    
    def get_commodities(self) -> Dict[str, Any]:
        """获取大宗商品价格"""
        try:
            df = ak.futures_global_spot_em()
            if df is None or df.empty:
                return {'gold': {'price': 0, 'unit': 'USD/oz'}, 'oil_wti': {'price': 0, 'unit': 'USD/barrel'}, 'copper': {'price': 0, 'unit': 'USD/ton'}}
            
            result = {}
            # 黄金
            gold_rows = df[df['合约名称'].str.contains('黄金|纽约金|XAU', na=False)]
            if not gold_rows.empty:
                row = gold_rows.iloc[0]
                price = float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0
                result['gold'] = {'price': price, 'unit': 'USD/oz'}
            else:
                result['gold'] = {'price': 0, 'unit': 'USD/oz'}
            
            # 原油
            oil_rows = df[df['合约名称'].str.contains('原油|WTI|布伦特', na=False)]
            if not oil_rows.empty:
                row = oil_rows.iloc[0]
                price = float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0
                result['oil_wti'] = {'price': price, 'unit': 'USD/barrel'}
            else:
                result['oil_wti'] = {'price': 0, 'unit': 'USD/barrel'}
            
            # 铜
            copper_rows = df[df['合约名称'].str.contains('铜|LME铜', na=False)]
            if not copper_rows.empty:
                row = copper_rows.iloc[0]
                price = float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0
                result['copper'] = {'price': price, 'unit': 'USD/ton'}
            else:
                result['copper'] = {'price': 0, 'unit': 'USD/ton'}
            
            return result
        except Exception as e:
            print(f"[MarketData] 获取大宗商品失败: {e}")
            return {'gold': {'price': 0, 'unit': 'USD/oz'}, 'oil_wti': {'price': 0, 'unit': 'USD/barrel'}, 'copper': {'price': 0, 'unit': 'USD/ton'}}
    
    def get_forex(self) -> Dict[str, Any]:
        """获取外汇数据"""
        try:
            result = {}
            # 美元指数
            try:
                df_usd = ak.forex_spot_em()
                if df_usd is not None and not df_usd.empty:
                    usd_row = df_usd[df_usd['货币对'].str.contains('美元指数', na=False)]
                    if not usd_row.empty:
                        price = float(usd_row.iloc[0].get('最新价', 0)) if pd.notna(usd_row.iloc[0].get('最新价')) else 0
                        result['usd_index'] = {'price': price}
                    else:
                        result['usd_index'] = {'price': 0}
                else:
                    result['usd_index'] = {'price': 0}
            except Exception as e:
                print(f"[MarketData] 获取美元指数失败: {e}")
                result['usd_index'] = {'price': 0}
            
            # USD/CNH
            try:
                df_cnh = ak.forex_hist_em("USDCNH")
                if df_cnh is not None and not df_cnh.empty:
                    latest = df_cnh.iloc[-1]
                    price = float(latest.get('收盘', 0)) if pd.notna(latest.get('收盘')) else 0
                    result['usdcnh'] = {'price': price}
                else:
                    result['usdcnh'] = {'price': 0}
            except Exception as e:
                print(f"[MarketData] 获取USDCNH失败: {e}")
                result['usdcnh'] = {'price': 0}
            
            # USD/CNY
            try:
                df_cny = ak.forex_hist_em("USDCNY")
                if df_cny is not None and not df_cny.empty:
                    latest = df_cny.iloc[-1]
                    price = float(latest.get('收盘', 0)) if pd.notna(latest.get('收盘')) else 0
                    result['usdcny'] = {'price': price}
                else:
                    result['usdcny'] = {'price': 0}
            except Exception as e:
                print(f"[MarketData] 获取USDCNY失败: {e}")
                result['usdcny'] = {'price': 0}
            
            return result
        except Exception as e:
            print(f"[MarketData] 获取外汇数据失败: {e}")
            return {'usd_index': {'price': 0}, 'usdcny': {'price': 0}, 'usdcnh': {'price': 0}}
    
    def collect_international_snapshot(self) -> Dict[str, Any]:
        """采集国际市场快照"""
        result = {
            'status': 'ok',
            'us_indices': {},
            'commodities': {},
            'forex': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            result['us_indices'] = self.get_us_indices()
        except Exception as e:
            result['us_indices'] = {}
            print(f"[MarketData] US indices采集失败: {e}")
        
        try:
            result['commodities'] = self.get_commodities()
        except Exception as e:
            result['commodities'] = {}
            print(f"[MarketData] 大宗商品采集失败: {e}")
        
        try:
            result['forex'] = self.get_forex()
        except Exception as e:
            result['forex'] = {}
            print(f"[MarketData] 外汇采集失败: {e}")
        
        # 检查是否需要降级
        if not result['us_indices'] and not result['commodities'] and not result['forex']:
            result['status'] = 'degraded'
        
        return result


international_data_collector = InternationalDataCollector()

