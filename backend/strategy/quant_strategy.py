"""
量化策略模块 - 基于技术指标的股票信号生成

使用均线、RSI、成交量等指标综合判断买卖信号
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List


class QuantStrategy:
    """量化策略：技术分析信号生成"""

    def analyze_stock(self, stock_code: str, kline: pd.DataFrame) -> Dict[str, Any]:
        """
        对单只股票进行技术分析

        Args:
            stock_code: 股票代码
            kline: K线数据 DataFrame，包含 date/open/close/high/low/volume

        Returns:
            {
                'signal': 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell',
                'confidence': float (0-1),
                'factors': [{'name': '...', 'value': '...', 'direction': 'up'|'down'}]
            }
        """
        if kline is None or kline.empty or len(kline) < 20:
            return {'signal': 'hold', 'confidence': 0.0, 'factors': []}

        df = kline.copy()

        # 确保数据类型
        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['close'])
        if len(df) < 20:
            return {'signal': 'hold', 'confidence': 0.0, 'factors': []}

        factors = []
        score = 0  # -100 到 +100

        # 1. 均线分析
        ma_score, ma_factors = self._analyze_ma(df)
        score += ma_score
        factors.extend(ma_factors)

        # 2. RSI 分析
        rsi_score, rsi_factors = self._analyze_rsi(df)
        score += rsi_score
        factors.extend(rsi_factors)

        # 3. 成交量分析
        vol_score, vol_factors = self._analyze_volume(df)
        score += vol_score
        factors.extend(vol_factors)

        # 4. 价格动量
        mom_score, mom_factors = self._analyze_momentum(df)
        score += mom_score
        factors.extend(mom_factors)

        # 综合判定
        signal, confidence = self._score_to_signal(score)

        return {
            'signal': signal,
            'confidence': confidence,
            'factors': factors
        }

    def _analyze_ma(self, df: pd.DataFrame):
        """均线分析: MA5/MA10/MA20"""
        factors = []
        score = 0

        close = df['close']
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()

        last_close = close.iloc[-1]
        last_ma5 = ma5.iloc[-1]
        last_ma10 = ma10.iloc[-1]
        last_ma20 = ma20.iloc[-1]

        if pd.isna(last_ma20):
            return 0, []

        # 短期均线在长期均线之上 → 多头排列
        if last_ma5 > last_ma10 > last_ma20:
            score += 25
            factors.append({'name': '均线多头排列', 'value': 'MA5>MA10>MA20', 'direction': 'up'})
        elif last_ma5 < last_ma10 < last_ma20:
            score -= 25
            factors.append({'name': '均线空头排列', 'value': 'MA5<MA10<MA20', 'direction': 'down'})

        # 金叉/死叉 (MA5 与 MA10)
        if len(ma5) >= 2 and len(ma10) >= 2:
            prev_ma5 = ma5.iloc[-2]
            prev_ma10 = ma10.iloc[-2]
            if not pd.isna(prev_ma5) and not pd.isna(prev_ma10):
                if prev_ma5 <= prev_ma10 and last_ma5 > last_ma10:
                    score += 15
                    factors.append({'name': 'MA5上穿MA10(金叉)', 'value': f'{last_ma5:.2f}>{last_ma10:.2f}', 'direction': 'up'})
                elif prev_ma5 >= prev_ma10 and last_ma5 < last_ma10:
                    score -= 15
                    factors.append({'name': 'MA5下穿MA10(死叉)', 'value': f'{last_ma5:.2f}<{last_ma10:.2f}', 'direction': 'down'})

        # 价格站上/跌破 MA20
        if last_close > last_ma20 * 1.02:
            score += 10
        elif last_close < last_ma20 * 0.98:
            score -= 10

        return score, factors

    def _analyze_rsi(self, df: pd.DataFrame):
        """RSI 相对强弱指标"""
        factors = []
        score = 0

        close = df['close']
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        last_avg_loss = avg_loss.iloc[-1]
        if pd.isna(last_avg_loss) or last_avg_loss == 0:
            return 0, []

        rs = avg_gain.iloc[-1] / last_avg_loss
        rsi = 100 - (100 / (1 + rs))

        if rsi < 30:
            score += 20
            factors.append({'name': 'RSI超卖', 'value': f'{rsi:.1f}', 'direction': 'up'})
        elif rsi < 40:
            score += 10
            factors.append({'name': 'RSI偏低', 'value': f'{rsi:.1f}', 'direction': 'up'})
        elif rsi > 70:
            score -= 20
            factors.append({'name': 'RSI超买', 'value': f'{rsi:.1f}', 'direction': 'down'})
        elif rsi > 60:
            score -= 10
            factors.append({'name': 'RSI偏高', 'value': f'{rsi:.1f}', 'direction': 'down'})

        return score, factors

    def _analyze_volume(self, df: pd.DataFrame):
        """成交量分析"""
        factors = []
        score = 0

        if 'volume' not in df.columns:
            return 0, []

        vol = df['volume']
        vol_ma5 = vol.rolling(5).mean()
        vol_ma20 = vol.rolling(20).mean()

        last_vol = vol.iloc[-1]
        last_vol_ma5 = vol_ma5.iloc[-1]
        last_vol_ma20 = vol_ma20.iloc[-1]

        if pd.isna(last_vol_ma20) or last_vol_ma20 == 0:
            return 0, []

        vol_ratio = last_vol / last_vol_ma20

        # 放量上涨
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]

        if vol_ratio > 2.0 and price_change > 0.02:
            score += 15
            factors.append({'name': '放量上涨', 'value': f'量比{vol_ratio:.1f}倍', 'direction': 'up'})
        elif vol_ratio > 2.0 and price_change < -0.02:
            score -= 15
            factors.append({'name': '放量下跌', 'value': f'量比{vol_ratio:.1f}倍', 'direction': 'down'})
        elif vol_ratio < 0.5:
            factors.append({'name': '缩量', 'value': f'量比{vol_ratio:.1f}倍', 'direction': 'down'})

        return score, factors

    def _analyze_momentum(self, df: pd.DataFrame):
        """价格动量分析"""
        factors = []
        score = 0

        close = df['close']

        # 近5日涨跌幅
        if len(close) >= 6:
            change_5d = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100
            if change_5d > 5:
                score += 10
                factors.append({'name': '5日动量强', 'value': f'{change_5d:+.1f}%', 'direction': 'up'})
            elif change_5d < -5:
                score -= 10
                factors.append({'name': '5日动量弱', 'value': f'{change_5d:+.1f}%', 'direction': 'down'})

        # 近10日涨跌幅
        if len(close) >= 11:
            change_10d = (close.iloc[-1] - close.iloc[-11]) / close.iloc[-11] * 100
            if change_10d > 10:
                score += 5
            elif change_10d < -10:
                score -= 5
                factors.append({'name': '10日跌幅大', 'value': f'{change_10d:+.1f}%', 'direction': 'down'})

        return score, factors

    def _score_to_signal(self, score: int):
        """将综合评分转换为信号和置信度"""
        if score >= 50:
            return 'strong_buy', min(0.95, 0.7 + (score - 50) / 200)
        elif score >= 25:
            return 'buy', 0.6 + (score - 25) / 100
        elif score <= -50:
            return 'strong_sell', min(0.95, 0.7 + (-score - 50) / 200)
        elif score <= -25:
            return 'sell', 0.6 + (-score - 25) / 100
        else:
            return 'hold', 0.3 + abs(score) / 100
