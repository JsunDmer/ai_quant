import json

from fastapi import APIRouter, Query

from stock_mvp.db import db


router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/latest")
def get_latest_signals(
    limit: int = Query(default=200, ge=1, le=1000),
    signal: str | None = None,
):
    rows = db.get_latest_stock_signals(signal=signal, limit=limit)

    def _loads(s, default):
        try:
            return json.loads(s) if s else default
        except Exception:
            return default

    items = []
    for r in rows:
        items.append(
            {
                "trade_date": r.trade_date,
                "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "sector_name": r.sector_name,
                "signal": r.signal,
                "confidence": r.confidence,
                "factors": _loads(r.factors_json, []),
                "created_at": r.created_at,
            }
        )

    trade_date = items[0]["trade_date"] if items else None
    return {"trade_date": trade_date, "items": items}

