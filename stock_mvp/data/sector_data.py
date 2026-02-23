"""
板块数据模块 - 板块价值评分与推荐
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import akshare as ak
import pandas as pd

from db import Database, SectorStock


class SectorData:
    """板块数据分析"""

    def __init__(self):
        self._db = Database()

    def get_sector_list(self) -> List[Dict[str, Any]]:
        """获取板块列表"""
        try:
            df = ak.stock_board_industry_name_em()
            sectors = []
            for _, row in df.iterrows():
                sectors.append({
                    'name': row['板块名称'],
                    'change': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                    'stock_count': int(row['股票数量']) if '股票数量' in row else 0
                })
            return sectors
        except Exception as e:
            print(f"获取板块列表失败: {e}")
            return []

    def get_sector_stocks(self, sector_name: str, trade_date: str = None) -> List[Dict[str, Any]]:
        """
        获取板块成分股（优先使用当天缓存）

        策略：
        1. 如果当天已有缓存 → 直接返回
        2. 否则从 akshare 拉取 → 存入缓存 → 返回
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        # 1. 查缓存
        cached = self._db.get_sector_stocks(sector_name, trade_date)
        if cached:
            print(f"[SectorData] {sector_name} 使用缓存 ({len(cached)}只, {trade_date})")
            return [
                {'code': s.stock_code, 'name': s.stock_name,
                 'price': s.price, 'change': s.change_pct}
                for s in cached
            ]

        # 2. 从 akshare 拉取
        stocks = self._fetch_sector_stocks_from_api(sector_name)

        # 3. 存入缓存
        if stocks:
            self._db.save_sector_stocks(sector_name, trade_date, stocks)
            print(f"[SectorData] {sector_name} 已缓存 {len(stocks)} 只个股")

        return stocks

    def get_sector_stocks_with_history(self, sector_name: str) -> List[Dict[str, Any]]:
        """
        获取板块成分股（允许使用历史缓存）

        策略：当天无数据时也可以返回历史缓存的个股列表
        """
        today = datetime.now().strftime('%Y-%m-%d')

        # 先尝试当天数据
        stocks = self.get_sector_stocks(sector_name, today)
        if stocks:
            return stocks

        # 回退到最新历史缓存
        cached = self._db.get_sector_stocks(sector_name)
        if cached:
            cache_date = cached[0].trade_date
            print(f"[SectorData] {sector_name} 使用历史缓存 ({len(cached)}只, {cache_date})")
            return [
                {'code': s.stock_code, 'name': s.stock_name,
                 'price': s.price, 'change': s.change_pct}
                for s in cached
            ]

        return []

    def _fetch_sector_stocks_from_api(self, sector_name: str) -> List[Dict[str, Any]]:
        """从 akshare 拉取板块成分股"""
        try:
            df = ak.stock_board_industry_cons_em(symbol=sector_name)
            stocks = []
            for _, row in df.head(20).iterrows():
                stocks.append({
                    'code': row['代码'],
                    'name': row['名称'],
                    'price': float(row['最新价']) if pd.notna(row.get('最新价', 0)) else 0,
                    'change': float(row['涨跌幅']) if pd.notna(row.get('涨跌幅', 0)) else 0
                })
            return stocks
        except Exception as e:
            print(f"获取板块成分股失败 ({sector_name}): {e}")
            return []

    def get_sector_fund_flow(self, sector_name: str) -> Dict[str, Any]:
        """获取板块资金流向"""
        try:
            df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
            # 兼容新旧字段名
            name_col = '名称' if '名称' in df.columns else '板块名称'
            row = df[df[name_col] == sector_name]
            if not row.empty:
                r = row.iloc[0]
                inflow_col = next((c for c in r.index if '主力净流入' in c and '净额' in c), None)
                pct_col = next((c for c in r.index if '主力净流入' in c and '净占比' in c), None)
                return {
                    'main_inflow': float(r[inflow_col]) if inflow_col else 0,
                    'main_inflow_pct': float(r[pct_col]) if pct_col else 0
                }
        except Exception as e:
            print(f"获取板块资金流向失败: {e}")
        return {'main_inflow': 0, 'main_inflow_pct': 0}

    def score_sector(self, sector_name: str) -> Dict[str, Any]:
        """
        板块评分：资金 + 估值 + 趋势
        """
        score = 0
        reasons = []

        # 1. 资金流向评分 (30%)
        try:
            fund_flow = self.get_sector_fund_flow(sector_name)
            inflow = fund_flow.get('main_inflow', 0)
            if inflow > 0:
                score += 30
                reasons.append(f"资金净流入{inflow/10000:.1f}亿")
            elif inflow < -50000:
                score -= 10
                reasons.append(f"资金净流出{abs(inflow)/10000:.1f}亿")
            else:
                score += 10
                reasons.append("资金进出平衡")
        except:
            reasons.append("资金数据获取失败")

        # 2. 涨跌幅趋势评分 (25%)
        try:
            sectors = self.get_sector_list()
            sector = next((s for s in sectors if s['name'] == sector_name), None)
            if sector:
                change = sector.get('change', 0)
                if change > 5:
                    score += 25
                    reasons.append(f"今日涨幅{change:.1f}%")
                elif change > 0:
                    score += 15
                    reasons.append(f"小幅上涨{change:.1f}%")
                elif change < -3:
                    score -= 15
                    reasons.append(f"下跌{abs(change):.1f}%")
                else:
                    score += 5
                    reasons.append("横盘整理")
        except:
            reasons.append("趋势数据获取失败")

        # 3. 综合评分 (满分55: 资金30 + 趋势25)
        if score >= 40:
            bucket = 'strong_recommend'
        elif score >= 20:
            bucket = 'watch'
        else:
            bucket = 'hold'

        return {
            'sector_name': sector_name,
            'score': score,
            'bucket': bucket,
            'reasons': reasons
        }

    def recommend_sectors(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        推荐板块：按评分分层
        """
        sectors = self.get_sector_list()
        results = {
            'strong_recommend': [],
            'watch': [],
            'hold': []
        }

        for sector in sectors[:30]:  # 取前30个板块
            scored = self.score_sector(sector['name'])
            results[scored['bucket']].append(scored)

        return results

    def pick_candidates_for_sector(self, sector_name: str, min_count: int = 3,
                                   trade_date: str = None) -> List[Dict[str, Any]]:
        """
        板块内候选股票筛选（优先使用缓存）
        """
        stocks = self.get_sector_stocks(sector_name, trade_date)
        candidates = []

        for stock in stocks:
            if stock['price'] <= 0:
                continue

            # 按涨幅过滤，取前排股票
            if stock['change'] > 0:
                candidates.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'price': stock['price'],
                    'change': stock['change'],
                    'reason': f"板块内领涨{stock['change']:.1f}%"
                })

            if len(candidates) >= min_count:
                break

        return candidates


sector_data = SectorData()
