"""
板块预测评估引擎
对比 AI 板块预测与实际涨跌幅，计算 T+1/T+3/T+5 准确率
"""
from datetime import datetime
from typing import List, Dict, Optional

from db import Database, PredictionEvaluation


class SectorEvaluator:
    """板块预测评估器"""

    def __init__(self):
        self._db = Database()

    # ========== 内部方法 ==========

    def _compute_cumulative_change(self, sector_name: str, dates: List[str]) -> Optional[float]:
        """
        计算板块在给定交易日列表内的累计涨跌幅（复合收益）
        公式: ((1+r1/100) * (1+r2/100) * ... - 1) * 100
        任一日期缺数据则返回 None
        """
        if not dates:
            return None
        product = 1.0
        for d in dates:
            perfs = self._db.get_sector_daily_performance(d)
            found = None
            for p in perfs:
                if p.sector_name == sector_name:
                    found = p
                    break
            if found is None:
                return None
            product *= (1 + found.change_pct / 100)
        return (product - 1) * 100

    def _check_direction(self, predicted: str, actual_change: float) -> int:
        """
        判断预测方向是否正确
        up:      actual > 0  → 正确
        down:    actual < 0  → 正确
        neutral: |actual| < 0.5% → 正确
        """
        if predicted == "up":
            return 1 if actual_change > 0 else 0
        elif predicted == "down":
            return 1 if actual_change < 0 else 0
        elif predicted == "neutral":
            return 1 if abs(actual_change) < 0.5 else 0
        return 0

    # ========== 评估执行 ==========

    def evaluate_predictions(self, prediction_date: str) -> List[PredictionEvaluation]:
        """评估某天所有 AI 板块预测"""
        # 1. 读取该日期的预测
        predictions = self._db.get_ai_sector_analysis(prediction_date)
        if not predictions:
            return []

        # 2. 获取 T+1/T+3/T+5 交易日
        future_dates = self._db.get_next_n_trading_dates(prediction_date, 5)

        t1_dates = future_dates[:1] if len(future_dates) >= 1 else []
        t3_dates = future_dates[:3] if len(future_dates) >= 3 else []
        t5_dates = future_dates[:5] if len(future_dates) >= 5 else []

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results = []

        for pred in predictions:
            ev = PredictionEvaluation(
                prediction_date=prediction_date,
                sector_name=pred.sector_name,
                direction=pred.direction,
                confidence=pred.confidence,
                score_up=pred.score_up,
                score_down=pred.score_down,
                evaluated_at=now_str,
            )

            # T+1
            if t1_dates:
                actual = self._compute_cumulative_change(pred.sector_name, t1_dates)
                if actual is not None:
                    ev.actual_t1 = round(actual, 4)
                    ev.correct_t1 = self._check_direction(pred.direction, actual)

            # T+3
            if t3_dates:
                actual = self._compute_cumulative_change(pred.sector_name, t3_dates)
                if actual is not None:
                    ev.actual_t3 = round(actual, 4)
                    ev.correct_t3 = self._check_direction(pred.direction, actual)

            # T+5
            if t5_dates:
                actual = self._compute_cumulative_change(pred.sector_name, t5_dates)
                if actual is not None:
                    ev.actual_t5 = round(actual, 4)
                    ev.correct_t5 = self._check_direction(pred.direction, actual)

            results.append(ev)

        # 批量写入
        if results:
            self._db.batch_upsert_prediction_evaluations(results)

        return results

    def evaluate_all_pending(self) -> int:
        """扫描所有历史预测，对可评估的执行评估，返回评估记录数"""
        # 获取 ai_sector_analysis 中所有 distinct trade_date
        with self._db.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT trade_date FROM ai_sector_analysis ORDER BY trade_date"
            ).fetchall()
        all_dates = [row['trade_date'] for row in rows]

        total = 0
        for date in all_dates:
            # 检查是否已完整评估（T+5 都有值）
            existing = self._db.get_prediction_evaluations(date)
            if existing and all(e.correct_t5 is not None for e in existing):
                continue
            results = self.evaluate_predictions(date)
            total += len(results)

        return total

    # ========== 统计指标 ==========

    def get_accuracy_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        """
        总体准确率
        Returns: {t1: {total, correct, accuracy, pending}, t3: ..., t5: ...}
        """
        evs = self._get_evaluations(start_date, end_date)
        result = {}
        for key, attr_correct, attr_actual in [
            ("t1", "correct_t1", "actual_t1"),
            ("t3", "correct_t3", "actual_t3"),
            ("t5", "correct_t5", "actual_t5"),
        ]:
            total = sum(1 for e in evs if getattr(e, attr_correct) is not None)
            correct = sum(1 for e in evs if getattr(e, attr_correct) == 1)
            pending = sum(1 for e in evs if getattr(e, attr_correct) is None)
            accuracy = (correct / total * 100) if total > 0 else 0
            result[key] = {
                "total": total,
                "correct": correct,
                "accuracy": round(accuracy, 1),
                "pending": pending,
            }
        return result

    def get_accuracy_by_confidence(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """按置信度分组准确率: 低(1-3), 中(4-6), 高(7-10)"""
        evs = self._get_evaluations(start_date, end_date)
        groups = [
            {"group": "低(1-3)", "min": 1, "max": 3},
            {"group": "中(4-6)", "min": 4, "max": 6},
            {"group": "高(7-10)", "min": 7, "max": 10},
        ]
        result = []
        for g in groups:
            subset = [e for e in evs if g["min"] <= (e.confidence or 0) <= g["max"]]
            item = {"group": g["group"], "count": len(subset)}
            for key, attr in [("t1_accuracy", "correct_t1"), ("t3_accuracy", "correct_t3"), ("t5_accuracy", "correct_t5")]:
                evaluated = [e for e in subset if getattr(e, attr) is not None]
                correct = sum(1 for e in evaluated if getattr(e, attr) == 1)
                item[key] = round(correct / len(evaluated) * 100, 1) if evaluated else 0
            result.append(item)
        return result

    def get_accuracy_by_direction(self, start_date: str = None, end_date: str = None) -> Dict:
        """按方向分组准确率"""
        evs = self._get_evaluations(start_date, end_date)
        result = {}
        for direction in ["up", "down", "neutral"]:
            subset = [e for e in evs if e.direction == direction]
            dir_result = {"count": len(subset)}
            for key, attr in [("t1_accuracy", "correct_t1"), ("t3_accuracy", "correct_t3"), ("t5_accuracy", "correct_t5")]:
                evaluated = [e for e in subset if getattr(e, attr) is not None]
                correct = sum(1 for e in evaluated if getattr(e, attr) == 1)
                dir_result[key] = round(correct / len(evaluated) * 100, 1) if evaluated else 0
            result[direction] = dir_result
        return result

    def get_daily_accuracy_trend(self, days: int = 30) -> List[Dict]:
        """每日准确率趋势"""
        dates = self._db.get_all_prediction_dates()[:days]
        result = []
        for date in reversed(dates):  # 按时间正序
            evs = self._db.get_prediction_evaluations(date)
            item = {"date": date}
            for key, attr in [("t1_accuracy", "correct_t1"), ("t3_accuracy", "correct_t3"), ("t5_accuracy", "correct_t5")]:
                evaluated = [e for e in evs if getattr(e, attr) is not None]
                correct = sum(1 for e in evaluated if getattr(e, attr) == 1)
                item[key] = round(correct / len(evaluated) * 100, 1) if evaluated else None
                item[key.replace("accuracy", "count")] = len(evaluated)
            result.append(item)
        return result

    def get_evaluation_details(self, prediction_date: str = None, limit: int = 200) -> List[PredictionEvaluation]:
        """预测明细列表"""
        if prediction_date:
            return self._db.get_prediction_evaluations(prediction_date)
        # 返回最近的评估记录
        dates = self._db.get_all_prediction_dates()
        results = []
        for date in dates:
            evs = self._db.get_prediction_evaluations(date)
            results.extend(evs)
            if len(results) >= limit:
                break
        return results[:limit]

    def _get_evaluations(self, start_date: str = None, end_date: str = None) -> List[PredictionEvaluation]:
        """获取评估记录（带日期范围过滤）"""
        if start_date and end_date:
            return self._db.get_prediction_evaluations_range(start_date, end_date)
        # 返回所有
        dates = self._db.get_all_prediction_dates()
        results = []
        for date in dates:
            results.extend(self._db.get_prediction_evaluations(date))
        return results


# 模块级实例
sector_evaluator = SectorEvaluator()
