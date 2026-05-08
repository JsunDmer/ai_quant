from fastapi import APIRouter, Query

from backend.evaluation.recommendation_evaluator import recommendation_evaluator
from backend.evaluation.parameter_optimizer import strategy_parameter_optimizer
from backend.evaluation.portfolio_builder import portfolio_builder
from backend.evaluation.sector_evaluator import sector_evaluator
from backend.evaluation.trade_simulator import trade_simulator


router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/summary")
def get_summary(start_date: str | None = None, end_date: str | None = None):
    summary = sector_evaluator.get_accuracy_summary(start_date, end_date)
    return {"summary": summary}


@router.get("/trend")
def get_trend(days: int = Query(default=60, ge=1, le=365)):
    trend = sector_evaluator.get_daily_accuracy_trend(days)
    return {"trend": trend}


@router.get("/by-confidence")
def get_by_confidence(start_date: str | None = None, end_date: str | None = None):
    rows = sector_evaluator.get_accuracy_by_confidence(start_date, end_date)
    return {"items": rows}


@router.get("/by-direction")
def get_by_direction(start_date: str | None = None, end_date: str | None = None):
    rows = sector_evaluator.get_accuracy_by_direction(start_date, end_date)
    return {"items": rows}


@router.get("/details")
def get_details(prediction_date: str | None = None, limit: int = Query(default=200, ge=1, le=2000)):
    rows = sector_evaluator.get_evaluation_details(prediction_date=prediction_date, limit=limit)

    items = []
    for r in rows:
        items.append(
            {
                "prediction_date": r.prediction_date,
                "sector_name": r.sector_name,
                "direction": r.direction,
                "confidence": r.confidence,
                "score_up": r.score_up,
                "score_down": r.score_down,
                "actual_t1": r.actual_t1,
                "actual_t3": r.actual_t3,
                "actual_t5": r.actual_t5,
                "correct_t1": r.correct_t1,
                "correct_t3": r.correct_t3,
                "correct_t5": r.correct_t5,
                "evaluated_at": r.evaluated_at,
                "created_at": r.created_at,
            }
        )

    return {"items": items}


@router.post("/recommendations/run")
def run_recommendation_evaluation(
    recommendation_date: str | None = None,
    recent_days: int = Query(default=30, ge=1, le=365),
):
    if recommendation_date:
        evaluated = recommendation_evaluator.evaluate_for_date(recommendation_date)
        return {"mode": "single_date", "recommendation_date": recommendation_date, "evaluated": evaluated}
    evaluated = recommendation_evaluator.evaluate_recent(recent_days)
    return {"mode": "recent_days", "recent_days": recent_days, "evaluated": evaluated}


@router.get("/recommendations/summary")
def get_recommendation_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    recommendation_type: str | None = None,
    source: str | None = None,
    sector_name: str | None = None,
):
    summary = recommendation_evaluator.get_summary(
        start_date=start_date,
        end_date=end_date,
        recommendation_type=recommendation_type,
        source=source,
        sector_name=sector_name,
    )
    return {"summary": summary}


@router.get("/recommendations/details")
def get_recommendation_details(
    start_date: str | None = None,
    end_date: str | None = None,
    recommendation_type: str | None = None,
    source: str | None = None,
    sector_name: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
):
    rows = recommendation_evaluator.get_details(
        start_date=start_date,
        end_date=end_date,
        recommendation_type=recommendation_type,
        source=source,
        sector_name=sector_name,
        limit=limit,
    )
    items = []
    for row in rows:
        items.append(
            {
                "recommendation_date": row.recommendation_date,
                "recommendation_type": row.recommendation_type,
                "source": row.source,
                "stock_code": row.stock_code,
                "stock_name": row.stock_name,
                "sector_name": row.sector_name,
                "return_1d": row.return_1d,
                "return_3d": row.return_3d,
                "return_5d": row.return_5d,
                "sector_return_1d": row.sector_return_1d,
                "sector_return_3d": row.sector_return_3d,
                "sector_return_5d": row.sector_return_5d,
                "excess_return_1d": row.excess_return_1d,
                "excess_return_3d": row.excess_return_3d,
                "excess_return_5d": row.excess_return_5d,
                "is_positive_1d": row.is_positive_1d,
                "is_positive_3d": row.is_positive_3d,
                "is_positive_5d": row.is_positive_5d,
                "evaluated_at": row.evaluated_at,
                "created_at": row.created_at,
            }
        )
    return {"items": items}


@router.get("/recommendations/compare")
def get_recommendation_compare(
    start_date: str | None = None,
    end_date: str | None = None,
    recommendation_type: str | None = None,
    source: str | None = None,
    sector_name: str | None = None,
):
    items = recommendation_evaluator.get_type_source_comparison(
        start_date=start_date,
        end_date=end_date,
        recommendation_type=recommendation_type,
        source=source,
        sector_name=sector_name,
    )
    return {"items": items}


@router.post("/optimizer/run")
def run_parameter_optimizer(
    trials: int = Query(default=30, ge=2, le=200),
    start_date: str | None = None,
    end_date: str | None = None,
    min_samples: int = Query(default=30, ge=10, le=2000),
):
    result = strategy_parameter_optimizer.run(
        trials=trials,
        start_date=start_date,
        end_date=end_date,
        min_samples=min_samples,
    )
    return result


@router.get("/portfolio/suggest")
def get_portfolio_suggestion(
    trade_date: str | None = None,
    top_n: int = Query(default=8, ge=1, le=20),
    max_single_weight: float = Query(default=0.2, ge=0.05, le=0.6),
    max_sector_weight: float = Query(default=0.35, ge=0.1, le=0.8),
):
    return portfolio_builder.suggest(
        trade_date=trade_date,
        top_n=top_n,
        max_single_weight=max_single_weight,
        max_sector_weight=max_sector_weight,
    )


@router.post("/simulation/run")
def run_simulation(trade_date: str | None = None):
    if trade_date:
        created = trade_simulator.create_trades_from_signals(trade_date=trade_date)
        closed = trade_simulator.check_and_close_trades()
        return {"mode": "single_date", "trade_date": trade_date, "created": created, "closed": closed}
    result = trade_simulator.run_full_simulation()
    return {"mode": "full", **result}


@router.get("/simulation/summary")
def get_simulation_summary(
    start_date: str | None = None,
    end_date: str | None = None,
):
    summary = trade_simulator.get_summary(start_date=start_date, end_date=end_date)
    return {"summary": summary}


@router.get("/simulation/by-sector")
def get_simulation_by_sector(
    start_date: str | None = None,
    end_date: str | None = None,
):
    items = trade_simulator.get_performance_by_sector(start_date=start_date, end_date=end_date)
    return {"items": items}


@router.get("/simulation/daily-pnl")
def get_simulation_daily_pnl(days: int = Query(default=60, ge=10, le=365)):
    return {"items": trade_simulator.get_daily_pnl(days=days)}


@router.get("/simulation/details")
def get_simulation_details(limit: int = Query(default=80, ge=1, le=500)):
    rows = trade_simulator.get_trade_details(limit=limit)
    items = []
    for row in rows:
        items.append(
            {
                "trade_date": row.trade_date,
                "stock_code": row.stock_code,
                "stock_name": row.stock_name,
                "sector_name": row.sector_name,
                "signal": row.signal,
                "confidence": row.confidence,
                "entry_date": row.entry_date,
                "entry_price": row.entry_price,
                "exit_date": row.exit_date,
                "exit_price": row.exit_price,
                "exit_reason": row.exit_reason,
                "return_pct": row.return_pct,
                "holding_days": row.holding_days,
                "status": row.status,
            }
        )
    return {"items": items}

