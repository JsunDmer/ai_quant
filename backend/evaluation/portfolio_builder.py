"""
组合建议与风控提示（MVP）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.data.db import Database, StockSignal
from backend.evaluation.trade_simulator import MAX_HOLD_DAYS, STOP_LOSS_PCT, TAKE_PROFIT_PCT


class PortfolioBuilder:
    def __init__(self):
        self._db = Database()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _load_signals(self, trade_date: Optional[str] = None) -> tuple[str, List[StockSignal]]:
        if trade_date:
            rows = self._db.get_stock_signals(trade_date)
            return trade_date, rows

        rows = self._db.get_latest_stock_signals(limit=300)
        if not rows:
            return "", []
        latest_date = rows[0].trade_date
        return latest_date, [row for row in rows if row.trade_date == latest_date]

    def _build_candidates(self, rows: List[StockSignal], top_n: int) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for row in rows:
            if row.signal not in ("buy", "strong_buy"):
                continue
            if not row.stock_code:
                continue
            signal_boost = 1.15 if row.signal == "strong_buy" else 1.0
            confidence = max(0.0, min(1.0, self._safe_float(row.confidence, 0.0)))
            raw_score = max(0.01, confidence * signal_boost)
            candidates.append(
                {
                    "stock_code": row.stock_code,
                    "stock_name": row.stock_name,
                    "sector_name": row.sector_name or "未知板块",
                    "signal": row.signal,
                    "confidence": confidence,
                    "raw_score": raw_score,
                }
            )
        candidates.sort(key=lambda x: (x["raw_score"], x["confidence"]), reverse=True)
        return candidates[:top_n]

    def _allocate_weights(
        self,
        candidates: List[Dict[str, Any]],
        max_single_weight: float,
        max_sector_weight: float,
    ) -> Dict[str, float]:
        if not candidates:
            return {}

        total_raw = sum(row["raw_score"] for row in candidates)
        if total_raw <= 0:
            total_raw = float(len(candidates))

        weights = {row["stock_code"]: row["raw_score"] / total_raw for row in candidates}

        for _ in range(8):
            changed = False

            # 单票上限
            for code in list(weights):
                if weights[code] > max_single_weight:
                    weights[code] = max_single_weight
                    changed = True

            # 板块上限
            sector_to_codes: Dict[str, List[str]] = {}
            for row in candidates:
                sector_to_codes.setdefault(row["sector_name"], []).append(row["stock_code"])
            sector_weight_map = {
                sector: sum(weights.get(code, 0.0) for code in codes) for sector, codes in sector_to_codes.items()
            }
            for sector, sector_weight in sector_weight_map.items():
                if sector_weight <= max_sector_weight:
                    continue
                scale = max_sector_weight / max(sector_weight, 1e-6)
                for code in sector_to_codes.get(sector, []):
                    weights[code] *= scale
                changed = True

            total_weight = sum(weights.values())
            if total_weight >= 0.999 or total_weight <= 0:
                break

            remaining = 1.0 - total_weight
            if remaining <= 1e-6:
                break

            # 把剩余仓位分给尚有容量的股票
            sector_weight_map = {
                sector: sum(weights.get(code, 0.0) for code in codes) for sector, codes in sector_to_codes.items()
            }
            capacity_rows: List[Dict[str, float]] = []
            for row in candidates:
                code = row["stock_code"]
                sector = row["sector_name"]
                cap_single = max(0.0, max_single_weight - weights.get(code, 0.0))
                cap_sector = max(0.0, max_sector_weight - sector_weight_map.get(sector, 0.0))
                capacity = min(cap_single, cap_sector)
                if capacity <= 1e-6:
                    continue
                capacity_rows.append({"stock_code": code, "capacity": capacity, "raw_score": row["raw_score"]})

            if not capacity_rows:
                break

            capacity_raw_total = sum(row["raw_score"] for row in capacity_rows)
            if capacity_raw_total <= 0:
                capacity_raw_total = float(len(capacity_rows))

            for row in capacity_rows:
                share = row["raw_score"] / capacity_raw_total
                add_weight = min(row["capacity"], remaining * share)
                if add_weight <= 1e-8:
                    continue
                weights[row["stock_code"]] = weights.get(row["stock_code"], 0.0) + add_weight
                changed = True

            if not changed:
                break

        # 数值清理：仅在总仓位超 100% 时缩放回 100%
        total_weight = sum(weights.values())
        if total_weight > 1.0 + 1e-6:
            scale = 1.0 / total_weight
            for code in list(weights):
                weights[code] *= scale

        return weights

    def suggest(
        self,
        trade_date: Optional[str] = None,
        top_n: int = 8,
        max_single_weight: float = 0.2,
        max_sector_weight: float = 0.35,
    ) -> Dict[str, Any]:
        top_n = max(1, min(self._safe_int(top_n, 8), 20))
        max_single_weight = max(0.05, min(self._safe_float(max_single_weight, 0.2), 0.6))
        max_sector_weight = max(max_single_weight, min(self._safe_float(max_sector_weight, 0.35), 0.8))

        active_date, rows = self._load_signals(trade_date)
        candidates = self._build_candidates(rows, top_n=top_n)
        if not active_date or not candidates:
            return {
                "trade_date": active_date,
                "constraints": {
                    "top_n": top_n,
                    "max_single_weight": max_single_weight,
                    "max_sector_weight": max_sector_weight,
                },
                "summary": {
                    "selected_count": 0,
                    "cash_weight": 1.0,
                    "max_single_weight_actual": 0.0,
                    "max_sector_weight_actual": 0.0,
                    "avg_confidence": 0.0,
                },
                "items": [],
                "risk_hints": ["暂无可用买入信号，建议先执行盘后分析链路。"],
            }

        weights = self._allocate_weights(
            candidates=candidates,
            max_single_weight=max_single_weight,
            max_sector_weight=max_sector_weight,
        )
        items: List[Dict[str, Any]] = []
        sector_weight_map: Dict[str, float] = {}

        for row in candidates:
            weight = weights.get(row["stock_code"], 0.0)
            if weight <= 0:
                continue
            sector = row["sector_name"]
            sector_weight_map[sector] = sector_weight_map.get(sector, 0.0) + weight
            items.append(
                {
                    "stock_code": row["stock_code"],
                    "stock_name": row["stock_name"],
                    "sector_name": sector,
                    "signal": row["signal"],
                    "confidence": round(row["confidence"], 4),
                    "weight": round(weight, 4),
                    "weight_pct": round(weight * 100, 2),
                    "risk_plan": {
                        "stop_loss_pct": STOP_LOSS_PCT,
                        "take_profit_pct": TAKE_PROFIT_PCT,
                        "max_hold_days": MAX_HOLD_DAYS,
                    },
                }
            )
        items.sort(key=lambda x: x["weight"], reverse=True)

        total_weight = sum(row["weight"] for row in items)
        cash_weight = max(0.0, round(1.0 - total_weight, 4))
        max_single_actual = max((row["weight"] for row in items), default=0.0)
        max_sector_actual = max(sector_weight_map.values(), default=0.0)
        avg_confidence = (
            sum(self._safe_float(row.get("confidence")) for row in items) / len(items) if items else 0.0
        )

        risk_hints: List[str] = []
        if cash_weight > 0.25:
            risk_hints.append("可用信号不足，组合存在较高现金仓位。")
        if max_single_actual >= max_single_weight * 0.95:
            risk_hints.append("头部个股权重接近上限，建议关注个股事件风险。")
        if max_sector_actual >= max_sector_weight * 0.95:
            risk_hints.append("板块集中度接近上限，建议分散行业暴露。")
        if avg_confidence < 0.62:
            risk_hints.append("整体信号置信度偏低，建议降低仓位或分批建仓。")
        if not risk_hints:
            risk_hints.append("当前组合分散度与仓位约束正常。")

        return {
            "trade_date": active_date,
            "constraints": {
                "top_n": top_n,
                "max_single_weight": max_single_weight,
                "max_sector_weight": max_sector_weight,
            },
            "summary": {
                "selected_count": len(items),
                "cash_weight": cash_weight,
                "max_single_weight_actual": round(max_single_actual, 4),
                "max_sector_weight_actual": round(max_sector_actual, 4),
                "avg_confidence": round(avg_confidence, 4),
            },
            "items": items,
            "sector_weights": [
                {"sector_name": sector, "weight": round(weight, 4), "weight_pct": round(weight * 100, 2)}
                for sector, weight in sorted(sector_weight_map.items(), key=lambda x: x[1], reverse=True)
            ],
            "risk_hints": risk_hints,
        }


portfolio_builder = PortfolioBuilder()

