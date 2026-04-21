"""
模拟交易引擎
根据 stock_signals 表的买入信号自动模拟建仓，
按止损/止盈/最大持仓天数规则自动平仓，计算收益率和胜率。
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from backend.data.db import Database, SimulatedTrade
from backend.data.stock_data import StockData

# 交易规则常量
STOP_LOSS_PCT = -5.0       # 止损 -5%
TAKE_PROFIT_PCT = 10.0     # 止盈 +10%
MAX_HOLD_DAYS = 10          # 最大持仓 10 个交易日
MIN_SECTOR_CONFIDENCE = 5   # AI板块分析最低置信度 (1-10)
MIN_SECTOR_REC_SCORE = 45   # 板块推荐最低评分


class TradeSimulator:
    def __init__(self):
        self._db = Database()
        self._stock_data = StockData()

    # ========== 建仓逻辑 ==========

    def create_trades_from_signals(self, trade_date: str = None) -> int:
        """从 stock_signals 中读取买入信号，创建模拟交易。
        只买入 AI 判定为上涨且置信度 >= MIN_SECTOR_CONFIDENCE 的板块中的股票。
        返回新建交易数。
        """
        if trade_date:
            dates_to_process = [trade_date]
        else:
            # 扫描所有有信号的日期
            dates_to_process = self._get_signal_dates_without_trades()

        created = 0
        for date in dates_to_process:
            # 构建可买入板块白名单: AI分析看涨 或 板块推荐评分达标
            bullish_sectors = self._get_bullish_sectors(date)

            signals = self._db.get_stock_signals(date)
            buy_signals = [s for s in signals if s.signal in ("buy", "strong_buy")]

            for sig in buy_signals:
                # 板块过滤：必须属于 AI 判定上涨且置信度达标的板块
                if sig.sector_name not in bullish_sectors:
                    continue

                # 跳过已有模拟交易的
                existing = self._db.get_trade_by_stock(date, sig.stock_code)
                if existing:
                    continue

                # 获取信号次日的开盘价作为 entry_price
                entry_date, entry_price = self._get_next_day_open(sig.stock_code, date)
                if not entry_date or entry_price is None or entry_price <= 0:
                    continue

                trade = SimulatedTrade(
                    trade_date=date,
                    stock_code=sig.stock_code,
                    stock_name=sig.stock_name,
                    sector_name=sig.sector_name,
                    signal=sig.signal,
                    confidence=sig.confidence,
                    entry_date=entry_date,
                    entry_price=entry_price,
                    status="open",
                )
                if self._db.upsert_simulated_trade(trade):
                    created += 1

        return created

    def _get_bullish_sectors(self, trade_date: str) -> set:
        """获取指定日期可买入的板块名集合。
        两种来源取并集:
        1. AI板块分析: direction='up' 且 confidence >= MIN_SECTOR_CONFIDENCE
        2. 板块推荐: bucket='strong_recommend' 且 score >= MIN_SECTOR_REC_SCORE
        """
        result = set()

        # 来源1: AI板块分析 (大类板块名)
        analyses = self._db.get_ai_sector_analysis(trade_date)
        for a in analyses:
            if a.direction == "up" and a.confidence >= MIN_SECTOR_CONFIDENCE:
                result.add(a.sector_name)

        # 来源2: 板块推荐 (AKShare细分板块名，与 stock_signals 的板块名一致)
        recs = self._db.get_sector_recommendations(trade_date)
        for r in recs:
            if r.bucket == "strong_recommend" and r.score >= MIN_SECTOR_REC_SCORE:
                result.add(r.sector_name)

        return result

    def _get_signal_dates_without_trades(self) -> List[str]:
        """找出有信号但还没创建模拟交易的日期"""
        with self._db.get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT ss.trade_date
                FROM stock_signals ss
                WHERE ss.signal IN ('buy', 'strong_buy')
                  AND NOT EXISTS (
                    SELECT 1 FROM simulated_trades st
                    WHERE st.trade_date = ss.trade_date AND st.stock_code = ss.stock_code
                  )
                ORDER BY ss.trade_date
            """).fetchall()
            return [row['trade_date'] for row in rows]

    def _get_next_day_open(self, stock_code: str, signal_date: str) -> tuple:
        """获取信号次日的开盘价。返回 (entry_date, entry_price)"""
        try:
            kline = self._stock_data.get_kline_data(stock_code, 60)
            if kline.empty:
                return None, None

            # date 列可能是 str 或 datetime
            kline['date'] = kline['date'].astype(str)
            # 找到 signal_date 之后的第一个交易日
            future = kline[kline['date'] > signal_date].sort_values('date')
            if future.empty:
                return None, None

            row = future.iloc[0]
            return str(row['date']), float(row['open'])
        except Exception as e:
            print(f"获取次日开盘价失败 {stock_code}: {e}")
            return None, None

    # ========== 平仓检查 ==========

    def check_and_close_trades(self) -> int:
        """检查所有 open 交易，判断是否触发平仓条件。返回平仓交易数。"""
        open_trades = self._db.get_open_trades()
        closed = 0

        for trade in open_trades:
            result = self._check_single_trade(trade)
            if result:
                exit_date, exit_price, exit_reason, holding_days = result
                return_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
                if self._db.close_trade(trade.id, exit_date, exit_price,
                                        exit_reason, return_pct, holding_days):
                    closed += 1

        return closed

    def _check_single_trade(self, trade: SimulatedTrade) -> Optional[tuple]:
        """检查单笔交易是否触发平仓。返回 (exit_date, exit_price, exit_reason, holding_days) 或 None"""
        try:
            kline = self._stock_data.get_kline_data(trade.stock_code, 60)
            if kline.empty:
                return None

            kline['date'] = kline['date'].astype(str)
            # 只看 entry_date 当天及之后的数据
            future = kline[kline['date'] >= trade.entry_date].sort_values('date')
            if future.empty:
                return None

            stop_loss_price = trade.entry_price * (1 + STOP_LOSS_PCT / 100)
            take_profit_price = trade.entry_price * (1 + TAKE_PROFIT_PCT / 100)

            for idx, (_, row) in enumerate(future.iterrows()):
                day_num = idx + 1  # 第几个交易日（entry_date 算第1天）
                low = float(row['low'])
                high = float(row['high'])
                close = float(row['close'])
                date = str(row['date'])

                # 止损：当日最低价触发
                if low <= stop_loss_price:
                    return date, stop_loss_price, "stop_loss", day_num

                # 止盈：当日最高价触发
                if high >= take_profit_price:
                    return date, take_profit_price, "take_profit", day_num

                # 最大持仓天数：以收盘价平仓
                if day_num >= MAX_HOLD_DAYS:
                    return date, close, "max_hold", day_num

            return None
        except Exception as e:
            print(f"检查交易平仓失败 {trade.stock_code}: {e}")
            return None

    # ========== 一键刷新 ==========

    def run_full_simulation(self) -> Dict:
        """一键执行: 建仓 + 平仓检查"""
        created = self.create_trades_from_signals()
        closed = self.check_and_close_trades()
        return {"created": created, "closed": closed}

    # ========== 统计指标 ==========

    def get_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        """总体统计"""
        all_trades = self._db.get_all_trades(start_date, end_date)
        closed = [t for t in all_trades if t.status == "closed"]
        open_trades = [t for t in all_trades if t.status == "open"]

        wins = [t for t in closed if t.return_pct > 0]
        losses = [t for t in closed if t.return_pct <= 0]

        total_profit = sum(t.return_pct for t in wins) if wins else 0
        total_loss = abs(sum(t.return_pct for t in losses)) if losses else 0

        return {
            "total_trades": len(all_trades),
            "closed_trades": len(closed),
            "open_trades": len(open_trades),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": len(wins) / len(closed) * 100 if closed else 0,
            "avg_return": sum(t.return_pct for t in closed) / len(closed) if closed else 0,
            "total_return": sum(t.return_pct for t in closed),
            "max_return": max((t.return_pct for t in closed), default=0),
            "min_return": min((t.return_pct for t in closed), default=0),
            "avg_holding_days": sum(t.holding_days for t in closed) / len(closed) if closed else 0,
            "profit_factor": total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0,
        }

    def get_performance_by_sector(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """按板块分组统计"""
        all_trades = self._db.get_all_trades(start_date, end_date)
        closed = [t for t in all_trades if t.status == "closed"]

        sector_map = defaultdict(list)
        for t in closed:
            sector_map[t.sector_name].append(t)

        result = []
        for sector, trades in sorted(sector_map.items(), key=lambda x: len(x[1]), reverse=True):
            wins = sum(1 for t in trades if t.return_pct > 0)
            result.append({
                "sector": sector,
                "count": len(trades),
                "win_rate": wins / len(trades) * 100 if trades else 0,
                "avg_return": sum(t.return_pct for t in trades) / len(trades),
            })
        return result

    def get_performance_by_confidence(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """按置信度分组统计: 低(0-0.6), 中(0.6-0.8), 高(0.8-1.0)"""
        all_trades = self._db.get_all_trades(start_date, end_date)
        closed = [t for t in all_trades if t.status == "closed"]

        groups = [
            ("低(0-0.6)", 0, 0.6),
            ("中(0.6-0.8)", 0.6, 0.8),
            ("高(0.8-1.0)", 0.8, 1.01),
        ]

        result = []
        for label, lo, hi in groups:
            trades = [t for t in closed if lo <= t.confidence < hi]
            wins = sum(1 for t in trades if t.return_pct > 0)
            result.append({
                "group": label,
                "count": len(trades),
                "win_rate": wins / len(trades) * 100 if trades else 0,
                "avg_return": sum(t.return_pct for t in trades) / len(trades) if trades else 0,
            })
        return result

    def get_daily_pnl(self, days: int = 60) -> List[Dict]:
        """每日收益曲线: 按 exit_date 分组，计算每日已平仓交易的平均收益"""
        all_trades = self._db.get_trades_by_status("closed")
        if not all_trades:
            return []

        # 按 exit_date 分组
        daily_map = defaultdict(list)
        for t in all_trades:
            if t.exit_date:
                daily_map[t.exit_date].append(t)

        # 按日期排序，只取最近 N 天
        sorted_dates = sorted(daily_map.keys())
        if days and len(sorted_dates) > days:
            sorted_dates = sorted_dates[-days:]

        result = []
        cumulative = 0
        for date in sorted_dates:
            trades = daily_map[date]
            daily_return = sum(t.return_pct for t in trades) / len(trades)
            cumulative += daily_return
            result.append({
                "date": date,
                "daily_return": round(daily_return, 2),
                "cumulative_return": round(cumulative, 2),
                "trade_count": len(trades),
            })
        return result

    def get_trade_details(self, limit: int = 200) -> List[SimulatedTrade]:
        """交易明细列表"""
        all_trades = self._db.get_all_trades()
        return all_trades[:limit]


# 全局实例
trade_simulator = TradeSimulator()
