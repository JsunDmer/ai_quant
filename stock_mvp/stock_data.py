"""
股票数据获取模块
使用 AKShare 统一获取 A 股实时行情和历史数据
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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
        """获取行情数据（带缓存，60秒内不重复下载）"""
        now = time.time()
        if self._spot_cache is None or (now - self._spot_cache_time) > self._cache_duration:
            print("正在下载行情数据...")
            self._spot_cache = ak.stock_zh_a_spot_em()
            self._spot_cache_time = now
            print(f"行情数据下载完成，共 {len(self._spot_cache)} 只股票")
        return self._spot_cache
    
    def search_stock(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索股票"""
        try:
            df = self._get_spot_data()
            
            # 精确匹配股票代码
            exact = df[df['代码'] == keyword]
            if not exact.empty:
                return exact[['代码', '名称']].to_dict('records')
            
            # 模糊匹配名称
            result = df[df['名称'].str.contains(keyword, na=False)].head(20)
            return result[['代码', '名称']].to_dict('records')
        except Exception as e:
            print(f"搜索股票失败: {e}")
            return []
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取实时行情"""
        try:
            df = self._get_spot_data()
            stock = df[df['代码'] == stock_code]
            if stock.empty:
                return None
            
            row = stock.iloc[0]
            return {
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
        except Exception as e:
            print(f"获取实时行情失败: {e}")
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
    
    def get_kline_data(self, stock_code: str, days: int = 60) -> pd.DataFrame:
        """获取 K 线数据"""
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'change_percent',
                '涨跌额': 'change_amount',
                '换手率': 'turnover_rate'
            })
            
            return df[['date', 'open', 'close', 'high', 'low', 'volume', 'change_percent']]
        except Exception as e:
            print(f"获取 K 线数据失败: {e}")
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


stock_data = StockData()
