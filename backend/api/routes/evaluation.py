from fastapi import APIRouter, Query

from stock_mvp.evaluation.sector_evaluator import sector_evaluator


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

