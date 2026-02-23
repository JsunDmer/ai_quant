"""
市场数据模块 - 收盘后快照采集
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak
import time


class MarketData:
    """市场数据采集"""
    
    def __init__(self):
        self._spot_cache = None
        self._spot_cache_time = 0
        self._cache_duration = 60
    
    def _get_spot_data(self) -> pd.DataFrame:
        now = time.time()
        if self._spot_cache is None or (now - self._spot_cache_time) > self._cache_duration:
            self._spot_cache = ak.stock_zh_a_spot_em()
            self._spot_cache_time = now
        return self._spot_cache
    
    def get_indices(self) -> List[Dict[str, Any]]:
        """获取大盘指数"""
        try:
            df = ak.stock_zh_index_spot_sina()
            indices = []
            for code in ['000001', '399001', '399006', '000688', '000300', '000905', '000852']:
                row = df[df['代码'] == code]
                if not row.empty:
                    r = row.iloc[0]
                    indices.append({
                        'code': code,
                        'name': r['名称'],
                        'price': float(r['最新价']) if pd.notna(r['最新价']) else 0,
                        'change': float(r['涨跌幅']) if pd.notna(r['涨跌幅']) else 0
                    })
            return indices
        except Exception as e:
            print(f"获取指数失败: {e}")
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
            
            return {
                'total': total,
                'up': up_count,
                'down': down_count,
                'flat': flat_count,
                'limit_up': limit_up,
                'limit_down': limit_down
            }
        except Exception as e:
            print(f"获取涨跌分布失败: {e}")
            return {'total': 0, 'up': 0, 'down': 0, 'flat': 0, 'limit_up': 0, 'limit_down': 0}
    
    def get_turnover(self) -> Dict[str, Any]:
        """获取成交额"""
        try:
            df = self._get_spot_data()
            total_amount = df['成交额'].sum() if '成交额' in df.columns else 0
            total_volume = df['成交量'].sum() if '成交量' in df.columns else 0
            return {
                'amount': float(total_amount) if pd.notna(total_amount) else 0,
                'volume': int(total_volume) if pd.notna(total_volume) else 0
            }
        except Exception as e:
            print(f"获取成交额失败: {e}")
            return {'amount': 0, 'volume': 0}
    
    def get_north_flow(self) -> Dict[str, Any]:
        """获取北向资金"""
        # 北向资金接口暂不可用，返回空数据
        return {'north': 0, 'south': 0}
    
    def get_news(self, limit: int = 10, enabled_sources: list = None) -> List[Dict[str, str]]:
        """获取财经新闻（多源采集，akshare 兜底）"""
        # 优先使用多源采集器
        try:
            from news_collector import collect_all_news
            news = collect_all_news(limit=limit, enabled_sources=enabled_sources)
            if news:
                return news
            print("多源采集返回空结果，尝试 akshare 兜底")
        except Exception as e:
            print(f"多源采集失败: {e}")

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
            print(f"akshare 兜底也失败: {e}")
            return []
    
    def collect_post_close_snapshot(self, trade_date: Optional[str] = None, enabled_sources: list = None) -> Dict[str, Any]:
        """
        采集收盘后市场快照
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
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
        except Exception as e:
            result['indices'] = []
            print(f"指数采集失败: {e}")
        
        try:
            result['market_breadth'] = self.get_market_breadth()
        except Exception as e:
            result['market_breadth'] = {}
            print(f"涨跌分布采集失败: {e}")
        
        try:
            result['turnover'] = self.get_turnover()
        except Exception as e:
            result['turnover'] = {}
            print(f"成交额采集失败: {e}")
        
        try:
            result['north_flow'] = self.get_north_flow()
        except Exception as e:
            result['north_flow'] = {}
            print(f"北向资金采集失败: {e}")
        
        try:
            result['news'] = self.get_news(enabled_sources=enabled_sources)
        except Exception as e:
            result['news'] = []
            print(f"快讯采集失败: {e}")
        
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
                    print(f"获取{name}失败: {e}")
                    result[name] = {'price': 0, 'change_pct': 0}
            return result
        except Exception as e:
            print(f"获取US indices失败: {e}")
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
            print(f"获取大宗商品失败: {e}")
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
                print(f"获取美元指数失败: {e}")
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
                print(f"获取USDCNH失败: {e}")
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
                print(f"获取USDCNY失败: {e}")
                result['usdcny'] = {'price': 0}
            
            return result
        except Exception as e:
            print(f"获取外汇数据失败: {e}")
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
            print(f"US indices采集失败: {e}")
        
        try:
            result['commodities'] = self.get_commodities()
        except Exception as e:
            result['commodities'] = {}
            print(f"大宗商品采集失败: {e}")
        
        try:
            result['forex'] = self.get_forex()
        except Exception as e:
            result['forex'] = {}
            print(f"外汇采集失败: {e}")
        
        # 检查是否需要降级
        if not result['us_indices'] and not result['commodities'] and not result['forex']:
            result['status'] = 'degraded'
        
        return result


international_data_collector = InternationalDataCollector()

