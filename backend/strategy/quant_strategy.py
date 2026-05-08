"""
量化策略模块 - 基于技术指标的股票信号生成

升级点：
1) 因子可配置权重（均线/RSI/成交量/动量）
2) 阈值可配置（buy/sell/strong）
3) 输出结构化 factor_scores，便于后续参数优化和诊断
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd


class QuantStrategy:
    """量化策略：技术分析信号生成（支持因子权重与阈值参数）"""

    FACTOR_KEYS = ("ma", "rsi", "volume", "momentum")
    DEFAULT_PARAMS: Dict[str, float] = {
        "weight_ma": 1.0,
        "weight_rsi": 1.0,
        "weight_volume": 1.0,
        "weight_momentum": 1.0,
        "buy_threshold": 25.0,
        "strong_buy_threshold": 50.0,
        "sell_threshold": -25.0,
        "strong_sell_threshold": -50.0,
    }

    def __init__(self, params: Dict[str, float] | None = None):
        self.params: Dict[str, float] = self.default_params()
        if params:
            self.update_params(params)

    @classmethod
    def default_params(cls) -> Dict[str, float]:
        return dict(cls.DEFAULT_PARAMS)

    def get_params(self) -> Dict[str, float]:
        return dict(self.params)

    def update_params(self, params: Dict[str, float]) -> None:
        for key, value in params.items():
            if key not in self.params:
                continue
            try:
                self.params[key] = float(value)
            except (TypeError, ValueError):
                continue
        self._normalize_thresholds()

    def _normalize_thresholds(self) -> None:
        buy = float(self.params.get("buy_threshold", 25.0))
        strong_buy = float(self.params.get("strong_buy_threshold", 50.0))
        sell = float(self.params.get("sell_threshold", -25.0))
        strong_sell = float(self.params.get("strong_sell_threshold", -50.0))

        if strong_buy <= buy:
            strong_buy = buy + 1.0
        if strong_sell >= sell:
            strong_sell = sell - 1.0

        self.params["buy_threshold"] = buy
        self.params["strong_buy_threshold"] = strong_buy
        self.params["sell_threshold"] = sell
        self.params["strong_sell_threshold"] = strong_sell

    @classmethod
    def _merged_params(cls, params: Dict[str, float] | None = None) -> Dict[str, float]:
        merged = cls.default_params()
        if params:
            for key, value in params.items():
                if key not in merged:
                    continue
                try:
                    merged[key] = float(value)
                except (TypeError, ValueError):
                    continue
        buy = merged["buy_threshold"]
        strong_buy = merged["strong_buy_threshold"]
        sell = merged["sell_threshold"]
        strong_sell = merged["strong_sell_threshold"]
        if strong_buy <= buy:
            merged["strong_buy_threshold"] = buy + 1.0
        if strong_sell >= sell:
            merged["strong_sell_threshold"] = sell - 1.0
        return merged

    @classmethod
    def compute_weighted_score(
        cls,
        raw_factor_scores: Dict[str, float],
        params: Dict[str, float] | None = None,
    ) -> float:
        active_params = cls._merged_params(params)
        score = 0.0
        for factor_key in cls.FACTOR_KEYS:
            raw_value = raw_factor_scores.get(factor_key, 0.0)
            weight = active_params.get(f"weight_{factor_key}", 1.0)
            try:
                score += float(raw_value) * float(weight)
            except (TypeError, ValueError):
                continue
        return round(score, 4)

    @classmethod
    def classify_score(
        cls,
        score: float,
        params: Dict[str, float] | None = None,
    ) -> Tuple[str, float]:
        active_params = cls._merged_params(params)
        strong_buy_threshold = active_params["strong_buy_threshold"]
        buy_threshold = active_params["buy_threshold"]
        sell_threshold = active_params["sell_threshold"]
        strong_sell_threshold = active_params["strong_sell_threshold"]

        signal = "hold"
        if score >= strong_buy_threshold:
            signal = "strong_buy"
        elif score >= buy_threshold:
            signal = "buy"
        elif score <= strong_sell_threshold:
            signal = "strong_sell"
        elif score <= sell_threshold:
            signal = "sell"

        max_ref = max(abs(strong_buy_threshold), abs(strong_sell_threshold), 1.0)
        normalized = min(1.0, abs(score) / max_ref)
        if signal in ("strong_buy", "strong_sell"):
            base = 0.72
        elif signal in ("buy", "sell"):
            base = 0.58
        else:
            base = 0.34
        confidence = min(0.98, round(base + normalized * 0.26, 4))
        return signal, confidence

    def analyze_stock(self, stock_code: str, kline: pd.DataFrame) -> Dict[str, Any]:
        """
        对单只股票进行技术分析。

        返回字段：
        - signal/confidence/factors: 兼容旧调用方
        - score/raw_score_total/factor_scores: 新增用于可观测性与参数优化
        """
        if kline is None or kline.empty or len(kline) < 20:
            return {
                "signal": "hold",
                "confidence": 0.0,
                "factors": [],
                "score": 0.0,
                "raw_score_total": 0.0,
                "factor_scores": {},
            }

        df = kline.copy()
        for col in ["open", "close", "high", "low", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["close"])
        if len(df) < 20:
            return {
                "signal": "hold",
                "confidence": 0.0,
                "factors": [],
                "score": 0.0,
                "raw_score_total": 0.0,
                "factor_scores": {},
            }

        factors: List[Dict[str, Any]] = []
        factor_scores: Dict[str, Dict[str, float | str]] = {}
        raw_score_total = 0.0

        analyzer_rows = [
            ("ma", "均线", self._analyze_ma(df)),
            ("rsi", "RSI", self._analyze_rsi(df)),
            ("volume", "成交量", self._analyze_volume(df)),
            ("momentum", "动量", self._analyze_momentum(df)),
        ]
        for key, label, (raw_score, details) in analyzer_rows:
            weight = float(self.params.get(f"weight_{key}", 1.0))
            weighted = float(raw_score) * weight
            raw_score_total += float(raw_score)
            factors.extend(details)
            factor_scores[key] = {
                "label": label,
                "raw": round(float(raw_score), 4),
                "weight": round(weight, 4),
                "weighted": round(weighted, 4),
            }

        total_score = self.compute_weighted_score(
            {k: float(v.get("raw", 0.0)) for k, v in factor_scores.items()},
            self.params,
        )
        signal, confidence = self.classify_score(total_score, self.params)

        return {
            "signal": signal,
            "confidence": confidence,
            "factors": factors,
            "score": total_score,
            "raw_score_total": round(raw_score_total, 4),
            "factor_scores": factor_scores,
            "strategy_params": self.get_params(),
        }

    def _analyze_ma(self, df: pd.DataFrame) -> Tuple[float, List[Dict[str, str]]]:
        """均线分析: MA5/MA10/MA20"""
        factors: List[Dict[str, str]] = []
        score = 0.0

        close = df["close"]
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()

        last_close = close.iloc[-1]
        last_ma5 = ma5.iloc[-1]
        last_ma10 = ma10.iloc[-1]
        last_ma20 = ma20.iloc[-1]

        if pd.isna(last_ma20):
            return 0.0, []

        if last_ma5 > last_ma10 > last_ma20:
            score += 25
            factors.append({"name": "均线多头排列", "value": "MA5>MA10>MA20", "direction": "up"})
        elif last_ma5 < last_ma10 < last_ma20:
            score -= 25
            factors.append({"name": "均线空头排列", "value": "MA5<MA10<MA20", "direction": "down"})

        if len(ma5) >= 2 and len(ma10) >= 2:
            prev_ma5 = ma5.iloc[-2]
            prev_ma10 = ma10.iloc[-2]
            if not pd.isna(prev_ma5) and not pd.isna(prev_ma10):
                if prev_ma5 <= prev_ma10 and last_ma5 > last_ma10:
                    score += 15
                    factors.append(
                        {
                            "name": "MA5上穿MA10(金叉)",
                            "value": f"{last_ma5:.2f}>{last_ma10:.2f}",
                            "direction": "up",
                        }
                    )
                elif prev_ma5 >= prev_ma10 and last_ma5 < last_ma10:
                    score -= 15
                    factors.append(
                        {
                            "name": "MA5下穿MA10(死叉)",
                            "value": f"{last_ma5:.2f}<{last_ma10:.2f}",
                            "direction": "down",
                        }
                    )

        if last_close > last_ma20 * 1.02:
            score += 10
        elif last_close < last_ma20 * 0.98:
            score -= 10

        return score, factors

    def _analyze_rsi(self, df: pd.DataFrame) -> Tuple[float, List[Dict[str, str]]]:
        """RSI 相对强弱指标"""
        factors: List[Dict[str, str]] = []
        score = 0.0

        close = df["close"]
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        last_avg_loss = avg_loss.iloc[-1]
        if pd.isna(last_avg_loss) or last_avg_loss == 0:
            return 0.0, []

        rs = avg_gain.iloc[-1] / last_avg_loss
        rsi = 100 - (100 / (1 + rs))

        if rsi < 30:
            score += 20
            factors.append({"name": "RSI超卖", "value": f"{rsi:.1f}", "direction": "up"})
        elif rsi < 40:
            score += 10
            factors.append({"name": "RSI偏低", "value": f"{rsi:.1f}", "direction": "up"})
        elif rsi > 70:
            score -= 20
            factors.append({"name": "RSI超买", "value": f"{rsi:.1f}", "direction": "down"})
        elif rsi > 60:
            score -= 10
            factors.append({"name": "RSI偏高", "value": f"{rsi:.1f}", "direction": "down"})

        return score, factors

    def _analyze_volume(self, df: pd.DataFrame) -> Tuple[float, List[Dict[str, str]]]:
        """成交量分析"""
        factors: List[Dict[str, str]] = []
        score = 0.0

        if "volume" not in df.columns:
            return 0.0, []

        vol = df["volume"]
        vol_ma20 = vol.rolling(20).mean()
        last_vol = vol.iloc[-1]
        last_vol_ma20 = vol_ma20.iloc[-1]

        if pd.isna(last_vol_ma20) or last_vol_ma20 == 0:
            return 0.0, []

        vol_ratio = last_vol / last_vol_ma20
        price_change = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]

        if vol_ratio > 2.0 and price_change > 0.02:
            score += 15
            factors.append({"name": "放量上涨", "value": f"量比{vol_ratio:.1f}倍", "direction": "up"})
        elif vol_ratio > 2.0 and price_change < -0.02:
            score -= 15
            factors.append({"name": "放量下跌", "value": f"量比{vol_ratio:.1f}倍", "direction": "down"})
        elif vol_ratio < 0.5:
            factors.append({"name": "缩量", "value": f"量比{vol_ratio:.1f}倍", "direction": "down"})

        return score, factors

    def _analyze_momentum(self, df: pd.DataFrame) -> Tuple[float, List[Dict[str, str]]]:
        """价格动量分析"""
        factors: List[Dict[str, str]] = []
        score = 0.0
        close = df["close"]

        if len(close) >= 6:
            change_5d = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100
            if change_5d > 5:
                score += 10
                factors.append({"name": "5日动量强", "value": f"{change_5d:+.1f}%", "direction": "up"})
            elif change_5d < -5:
                score -= 10
                factors.append({"name": "5日动量弱", "value": f"{change_5d:+.1f}%", "direction": "down"})

        if len(close) >= 11:
            change_10d = (close.iloc[-1] - close.iloc[-11]) / close.iloc[-11] * 100
            if change_10d > 10:
                score += 5
            elif change_10d < -10:
                score -= 5
                factors.append({"name": "10日跌幅大", "value": f"{change_10d:+.1f}%", "direction": "down"})

        return score, factors
