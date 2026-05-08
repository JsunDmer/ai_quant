"""
推荐评估引擎
评估个股推荐在 T+1/T+3/T+5 的收益、命中率与相对板块超额收益。
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from backend.data.db import Database, RecommendationEvaluation
from backend.data.stock_data import StockData


class RecommendationEvaluator:
    """推荐评估器（个股）"""

    def __init__(self):
        self._db = Database()
        self._stock_data = StockData()

    def _compute_forward_return(self, stock_code: str, recommendation_date: str, horizon_days: int) -> Optional[float]:
        """
        计算推荐日收盘到 T+horizon 收盘的收益率。
        返回百分比（如 1.23 表示 +1.23%）。
        """
        try:
            kline = self._stock_data.get_kline_data(stock_code, 260)
            if kline is None or kline.empty:
                return None
            if "date" not in kline.columns or "close" not in kline.columns:
                return None

            df = kline.copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
            if df.empty:
                return None

            df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
            base_rows = df.index[df["date_str"] == recommendation_date].tolist()
            if not base_rows:
                return None
            base_idx = base_rows[-1]
            target_idx = base_idx + horizon_days
            if target_idx >= len(df):
                return None

            base_close = float(df.iloc[base_idx]["close"])
            target_close = float(df.iloc[target_idx]["close"])
            if base_close <= 0:
                return None
            return round((target_close / base_close - 1) * 100, 4)
        except Exception:
            return None

    def _compute_sector_forward_return(self, sector_name: str, recommendation_date: str, horizon_days: int) -> Optional[float]:
        """计算板块在未来 N 个交易日的复合收益。"""
        if not sector_name:
            return None
        future_dates = self._db.get_next_n_trading_dates(recommendation_date, horizon_days)
        if len(future_dates) < horizon_days:
            return None
        dates = future_dates[:horizon_days]

        product = 1.0
        for date in dates:
            perfs = self._db.get_sector_daily_performance(date)
            found = None
            for perf in perfs:
                if perf.sector_name == sector_name:
                    found = perf
                    break
            if found is None:
                return None
            product *= (1 + float(found.change_pct or 0) / 100)
        return round((product - 1) * 100, 4)

    def _extract_index_change_from_snapshot(self, trade_date: str, index_code: str) -> Optional[float]:
        snapshot = self._db.get_market_snapshot(trade_date)
        if not snapshot or not snapshot.indices_json:
            return None
        try:
            indices = json.loads(snapshot.indices_json)
        except Exception:
            return None
        if not isinstance(indices, list):
            return None
        norm_code = (index_code or "").strip()
        for item in indices:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", "")).strip()
            if code != norm_code:
                continue
            raw_change = item.get("change")
            try:
                return float(raw_change or 0)
            except Exception:
                return None
        return None

    def _compute_index_forward_return(self, index_code: str, recommendation_date: str, horizon_days: int) -> Optional[float]:
        """使用 market_snapshots 的指数涨跌幅估算指数未来 N 日复合收益。"""
        future_dates = self._db.get_next_n_trading_dates(recommendation_date, horizon_days)
        if len(future_dates) < horizon_days:
            return None
        dates = future_dates[:horizon_days]
        product = 1.0
        for date in dates:
            day_change = self._extract_index_change_from_snapshot(date, index_code=index_code)
            if day_change is None:
                return None
            product *= (1 + day_change / 100)
        return round((product - 1) * 100, 4)

    def _compute_simple_momentum_baseline(self, recommendation_date: str, horizon_days: int) -> Optional[float]:
        """
        简单动量基准：
        选取 recommendation_date 当天涨幅最高的板块，计算其未来 N 日复合收益。
        """
        perfs = self._db.get_sector_daily_performance(recommendation_date)
        if not perfs:
            return None
        best = max(perfs, key=lambda item: float(item.change_pct or 0))
        sector_name = str(best.sector_name or "").strip()
        if not sector_name:
            return None
        return self._compute_sector_forward_return(
            sector_name=sector_name,
            recommendation_date=recommendation_date,
            horizon_days=horizon_days,
        )

    @staticmethod
    def _to_positive_flag(value: Optional[float]) -> Optional[int]:
        if value is None:
            return None
        return 1 if value > 0 else 0

    def _collect_signal_recommendations(self, trade_date: str) -> List[Tuple[str, str, str, str]]:
        items: List[Tuple[str, str, str, str]] = []
        rows = self._db.get_stock_signals(trade_date)
        for row in rows:
            if row.signal not in ("buy", "strong_buy"):
                continue
            if not row.stock_code:
                continue
            items.append((row.stock_code, row.stock_name, row.sector_name, "signal"))
        return items

    def _collect_sector_candidate_recommendations(self, trade_date: str) -> List[Tuple[str, str, str, str]]:
        items: List[Tuple[str, str, str, str]] = []
        rows = self._db.get_sector_stock_recommendations(trade_date)
        for row in rows:
            if not row.stock_code:
                continue
            items.append((row.stock_code, row.stock_name, row.sector_name, "sector_candidate"))
        return items

    def evaluate_for_date(self, recommendation_date: str) -> int:
        """评估指定日期推荐，返回写入记录数。"""
        if not recommendation_date:
            return 0

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        evaluations: List[RecommendationEvaluation] = []

        # 技术信号推荐
        for stock_code, stock_name, sector_name, source in self._collect_signal_recommendations(recommendation_date):
            r1 = self._compute_forward_return(stock_code, recommendation_date, 1)
            r3 = self._compute_forward_return(stock_code, recommendation_date, 3)
            r5 = self._compute_forward_return(stock_code, recommendation_date, 5)
            s1 = self._compute_sector_forward_return(sector_name, recommendation_date, 1)
            s3 = self._compute_sector_forward_return(sector_name, recommendation_date, 3)
            s5 = self._compute_sector_forward_return(sector_name, recommendation_date, 5)

            evaluations.append(
                RecommendationEvaluation(
                    recommendation_date=recommendation_date,
                    recommendation_type="stock_signal",
                    source=source,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    sector_name=sector_name,
                    return_1d=r1,
                    return_3d=r3,
                    return_5d=r5,
                    sector_return_1d=s1,
                    sector_return_3d=s3,
                    sector_return_5d=s5,
                    excess_return_1d=round(r1 - s1, 4) if (r1 is not None and s1 is not None) else None,
                    excess_return_3d=round(r3 - s3, 4) if (r3 is not None and s3 is not None) else None,
                    excess_return_5d=round(r5 - s5, 4) if (r5 is not None and s5 is not None) else None,
                    is_positive_1d=self._to_positive_flag(r1),
                    is_positive_3d=self._to_positive_flag(r3),
                    is_positive_5d=self._to_positive_flag(r5),
                    evaluated_at=now_str,
                )
            )

        # 板块候选推荐
        for stock_code, stock_name, sector_name, source in self._collect_sector_candidate_recommendations(recommendation_date):
            r1 = self._compute_forward_return(stock_code, recommendation_date, 1)
            r3 = self._compute_forward_return(stock_code, recommendation_date, 3)
            r5 = self._compute_forward_return(stock_code, recommendation_date, 5)
            s1 = self._compute_sector_forward_return(sector_name, recommendation_date, 1)
            s3 = self._compute_sector_forward_return(sector_name, recommendation_date, 3)
            s5 = self._compute_sector_forward_return(sector_name, recommendation_date, 5)

            evaluations.append(
                RecommendationEvaluation(
                    recommendation_date=recommendation_date,
                    recommendation_type="sector_candidate",
                    source=source,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    sector_name=sector_name,
                    return_1d=r1,
                    return_3d=r3,
                    return_5d=r5,
                    sector_return_1d=s1,
                    sector_return_3d=s3,
                    sector_return_5d=s5,
                    excess_return_1d=round(r1 - s1, 4) if (r1 is not None and s1 is not None) else None,
                    excess_return_3d=round(r3 - s3, 4) if (r3 is not None and s3 is not None) else None,
                    excess_return_5d=round(r5 - s5, 4) if (r5 is not None and s5 is not None) else None,
                    is_positive_1d=self._to_positive_flag(r1),
                    is_positive_3d=self._to_positive_flag(r3),
                    is_positive_5d=self._to_positive_flag(r5),
                    evaluated_at=now_str,
                )
            )

        if not evaluations:
            return 0
        self._db.batch_upsert_recommendation_evaluations(evaluations)
        return len(evaluations)

    def evaluate_recent(self, recent_days: int = 30) -> int:
        """评估最近 N 个推荐日。"""
        if recent_days <= 0:
            return 0
        with self._db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT trade_date as recommendation_date
                FROM (
                    SELECT trade_date FROM stock_signals
                    UNION ALL
                    SELECT trade_date FROM sector_stock_recommendations
                )
                ORDER BY recommendation_date DESC
                LIMIT ?
                """,
                (recent_days,),
            ).fetchall()
        dates = [row["recommendation_date"] for row in rows]

        total = 0
        for date in dates:
            total += self.evaluate_for_date(date)
        return total

    def _load_rows(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        recommendation_type: str | None = None,
        source: str | None = None,
        sector_name: str | None = None,
        limit: int = 5000,
    ) -> List[RecommendationEvaluation]:
        if start_date and end_date:
            return self._db.get_recommendation_evaluations_range(
                start_date,
                end_date,
                recommendation_type=recommendation_type,
                source=source,
                sector_name=sector_name,
                limit=limit,
            )
        if start_date and not end_date:
            return self._db.get_recommendation_evaluations_range(
                start_date,
                "9999-12-31",
                recommendation_type=recommendation_type,
                source=source,
                sector_name=sector_name,
                limit=limit,
            )
        if end_date and not start_date:
            return self._db.get_recommendation_evaluations_range(
                "0001-01-01",
                end_date,
                recommendation_type=recommendation_type,
                source=source,
                sector_name=sector_name,
                limit=limit,
            )
        return self._db.get_recommendation_evaluations(
            recommendation_date=None,
            recommendation_type=recommendation_type,
            source=source,
            sector_name=sector_name,
            limit=limit,
        )

    def get_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        recommendation_type: str | None = None,
        source: str | None = None,
        sector_name: str | None = None,
    ) -> Dict:
        """返回推荐评估摘要（命中率与平均收益）"""
        rows = self._load_rows(
            start_date=start_date,
            end_date=end_date,
            recommendation_type=recommendation_type,
            source=source,
            sector_name=sector_name,
        )

        hs300_cache: Dict[Tuple[str, str], Optional[float]] = {}
        momentum_cache: Dict[Tuple[str, str], Optional[float]] = {}

        def _metric(horizon: str) -> Dict:
            attr = f"return_{horizon}"
            excess_attr = f"excess_return_{horizon}"
            values = [getattr(row, attr) for row in rows if getattr(row, attr) is not None]
            excess_values = [getattr(row, excess_attr) for row in rows if getattr(row, excess_attr) is not None]
            sector_baseline_values = [
                getattr(row, f"sector_return_{horizon}")
                for row in rows
                if getattr(row, f"sector_return_{horizon}") is not None
            ]

            hs300_values: List[float] = []
            momentum_values: List[float] = []
            hs300_excess_values: List[float] = []
            momentum_excess_values: List[float] = []

            horizon_days = int(horizon.replace("d", ""))
            for row in rows:
                row_return = getattr(row, attr)
                if row_return is None:
                    continue
                date_key = row.recommendation_date

                hs300_key = (date_key, horizon)
                if hs300_key not in hs300_cache:
                    hs300_cache[hs300_key] = self._compute_index_forward_return(
                        index_code="000300",
                        recommendation_date=date_key,
                        horizon_days=horizon_days,
                    )
                hs300_return = hs300_cache[hs300_key]
                if hs300_return is not None:
                    hs300_values.append(hs300_return)
                    hs300_excess_values.append(round(row_return - hs300_return, 4))

                momentum_key = (date_key, horizon)
                if momentum_key not in momentum_cache:
                    momentum_cache[momentum_key] = self._compute_simple_momentum_baseline(
                        recommendation_date=date_key,
                        horizon_days=horizon_days,
                    )
                momentum_return = momentum_cache[momentum_key]
                if momentum_return is not None:
                    momentum_values.append(momentum_return)
                    momentum_excess_values.append(round(row_return - momentum_return, 4))

            hit_count = sum(1 for value in values if value > 0)
            evaluated_count = len(values)
            return {
                "evaluated_count": evaluated_count,
                "hit_count": hit_count,
                "hit_rate": round(hit_count / evaluated_count * 100, 1) if evaluated_count > 0 else 0.0,
                "avg_return": round(sum(values) / evaluated_count, 4) if evaluated_count > 0 else 0.0,
                "avg_excess_return_sector": round(sum(excess_values) / len(excess_values), 4) if excess_values else 0.0,
                "avg_baseline_sector_return": (
                    round(sum(sector_baseline_values) / len(sector_baseline_values), 4)
                    if sector_baseline_values
                    else 0.0
                ),
                "avg_baseline_hs300_return": (
                    round(sum(hs300_values) / len(hs300_values), 4) if hs300_values else 0.0
                ),
                "avg_excess_return_hs300": (
                    round(sum(hs300_excess_values) / len(hs300_excess_values), 4)
                    if hs300_excess_values
                    else 0.0
                ),
                "avg_baseline_momentum_return": (
                    round(sum(momentum_values) / len(momentum_values), 4) if momentum_values else 0.0
                ),
                "avg_excess_return_momentum": (
                    round(sum(momentum_excess_values) / len(momentum_excess_values), 4)
                    if momentum_excess_values
                    else 0.0
                ),
            }

        return {
            "total_recommendations": len(rows),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "recommendation_type": recommendation_type,
                "source": source,
                "sector_name": sector_name,
            },
            "t1": _metric("1d"),
            "t3": _metric("3d"),
            "t5": _metric("5d"),
        }

    def get_details(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        recommendation_type: str | None = None,
        source: str | None = None,
        sector_name: str | None = None,
        limit: int = 500,
    ) -> List[RecommendationEvaluation]:
        return self._load_rows(
            start_date=start_date,
            end_date=end_date,
            recommendation_type=recommendation_type,
            source=source,
            sector_name=sector_name,
            limit=limit,
        )


recommendation_evaluator = RecommendationEvaluator()

