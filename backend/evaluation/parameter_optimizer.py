"""
策略参数优化器（MVP）

基于历史 recommendation_evaluations + factor_scores，
对量化策略参数进行随机搜索，输出最优参数与基线对比。
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.data.db import Database, FactorScoreRecord, RecommendationEvaluation
from backend.strategy.quant_strategy import QuantStrategy


class StrategyParameterOptimizer:
    def __init__(self):
        self._db = Database()
        self._rng = random.Random(42)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _load_eval_rows(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20000,
    ) -> List[RecommendationEvaluation]:
        if start_date and end_date:
            rows = self._db.get_recommendation_evaluations_range(
                start_date=start_date,
                end_date=end_date,
                recommendation_type="stock_signal",
                source="signal",
                limit=limit,
            )
        else:
            rows = self._db.get_recommendation_evaluations(
                recommendation_date=None,
                recommendation_type="stock_signal",
                source="signal",
                limit=limit,
            )
            if start_date:
                rows = [row for row in rows if row.recommendation_date >= start_date]
            if end_date:
                rows = [row for row in rows if row.recommendation_date <= end_date]
        return [row for row in rows if row.return_5d is not None]

    def _load_factor_rows(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50000,
    ) -> List[FactorScoreRecord]:
        if start_date and end_date:
            return self._db.get_factor_scores_range(start_date=start_date, end_date=end_date, limit=limit)
        rows = self._db.get_factor_scores(limit=limit)
        if start_date:
            rows = [row for row in rows if row.trade_date >= start_date]
        if end_date:
            rows = [row for row in rows if row.trade_date <= end_date]
        return rows

    def _extract_raw_scores(self, factor_row: FactorScoreRecord) -> Dict[str, float]:
        try:
            parsed = json.loads(factor_row.factor_scores_json or "{}")
        except Exception:
            parsed = {}
        if not isinstance(parsed, dict):
            return {}

        raw_scores: Dict[str, float] = {}
        for key in QuantStrategy.FACTOR_KEYS:
            value = parsed.get(key)
            if isinstance(value, dict):
                raw_scores[key] = self._safe_float(value.get("raw"), 0.0)
            else:
                raw_scores[key] = self._safe_float(value, 0.0)
        return raw_scores

    def _build_samples(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        eval_rows = self._load_eval_rows(start_date=start_date, end_date=end_date)
        factor_rows = self._load_factor_rows(start_date=start_date, end_date=end_date)
        factor_map: Dict[tuple[str, str], Dict[str, float]] = {}
        for row in factor_rows:
            if not row.trade_date or not row.stock_code:
                continue
            factor_map[(row.trade_date, row.stock_code)] = self._extract_raw_scores(row)

        samples: List[Dict[str, Any]] = []
        for row in eval_rows:
            raw_scores = factor_map.get((row.recommendation_date, row.stock_code))
            if not raw_scores:
                continue
            if not any(abs(v) > 0 for v in raw_scores.values()):
                continue
            samples.append(
                {
                    "recommendation_date": row.recommendation_date,
                    "stock_code": row.stock_code,
                    "return_5d": self._safe_float(row.return_5d, 0.0),
                    "excess_return_5d": self._safe_float(row.excess_return_5d, 0.0),
                    "raw_scores": raw_scores,
                }
            )
        return samples

    def _evaluate_params(self, params: Dict[str, float], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        picked: List[Dict[str, Any]] = []
        for sample in samples:
            total_score = QuantStrategy.compute_weighted_score(sample["raw_scores"], params=params)
            signal, _ = QuantStrategy.classify_score(total_score, params=params)
            if signal in ("buy", "strong_buy"):
                picked.append(sample)

        if not picked:
            return {
                "picked_count": 0,
                "hit_count": 0,
                "hit_rate": 0.0,
                "avg_return_5d": 0.0,
                "avg_excess_return_5d": 0.0,
                "objective": -9999.0,
            }

        hit_count = sum(1 for row in picked if row["return_5d"] > 0)
        picked_count = len(picked)
        hit_rate = hit_count / picked_count * 100
        avg_return_5d = sum(row["return_5d"] for row in picked) / picked_count
        avg_excess_return_5d = sum(row["excess_return_5d"] for row in picked) / picked_count
        objective = hit_rate * 0.5 + avg_excess_return_5d * 15 + avg_return_5d * 5
        return {
            "picked_count": picked_count,
            "hit_count": hit_count,
            "hit_rate": round(hit_rate, 2),
            "avg_return_5d": round(avg_return_5d, 4),
            "avg_excess_return_5d": round(avg_excess_return_5d, 4),
            "objective": round(objective, 4),
        }

    def _sample_params(self) -> Dict[str, float]:
        buy_threshold = round(self._rng.uniform(16, 34), 2)
        strong_buy_threshold = round(self._rng.uniform(max(36.0, buy_threshold + 6), 65.0), 2)
        return {
            "weight_ma": round(self._rng.uniform(0.5, 1.7), 2),
            "weight_rsi": round(self._rng.uniform(0.5, 1.7), 2),
            "weight_volume": round(self._rng.uniform(0.4, 1.6), 2),
            "weight_momentum": round(self._rng.uniform(0.5, 1.8), 2),
            "buy_threshold": buy_threshold,
            "strong_buy_threshold": strong_buy_threshold,
            "sell_threshold": -buy_threshold,
            "strong_sell_threshold": -strong_buy_threshold,
        }

    def run(
        self,
        trials: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_samples: int = 30,
    ) -> Dict[str, Any]:
        trials = max(2, min(int(trials), 200))
        min_samples = max(1, int(min_samples))

        samples = self._build_samples(start_date=start_date, end_date=end_date)
        if len(samples) < min_samples:
            return {
                "status": "insufficient_data",
                "message": "可用于参数优化的样本不足，请先跑更多交易日并生成评估结果。",
                "sample_count": len(samples),
                "required_min_samples": min_samples,
                "filters": {"start_date": start_date, "end_date": end_date},
            }

        baseline_params = QuantStrategy.default_params()
        trials_rows: List[Dict[str, Any]] = []

        baseline_metrics = self._evaluate_params(baseline_params, samples)
        trials_rows.append(
            {
                "name": "baseline",
                "params": baseline_params,
                **baseline_metrics,
            }
        )

        for idx in range(trials - 1):
            params = self._sample_params()
            metrics = self._evaluate_params(params, samples)
            trials_rows.append(
                {
                    "name": f"trial_{idx + 1}",
                    "params": params,
                    **metrics,
                }
            )

        sorted_rows = sorted(trials_rows, key=lambda row: row.get("objective", -9999), reverse=True)
        best = sorted_rows[0]

        return {
            "status": "ok",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sample_count": len(samples),
            "filters": {"start_date": start_date, "end_date": end_date},
            "baseline": trials_rows[0],
            "best": best,
            "top_trials": sorted_rows[:10],
        }


strategy_parameter_optimizer = StrategyParameterOptimizer()

