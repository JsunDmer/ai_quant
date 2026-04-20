import json

from fastapi import APIRouter, HTTPException

from db import db


router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/latest")
def get_latest_market():
    snapshot = db.get_latest_market_snapshot()
    if not snapshot:
        raise HTTPException(status_code=404, detail="no market snapshot")

    def _loads(s, default):
        try:
            return json.loads(s) if s else default
        except Exception:
            return default

    return {
        "trade_date": snapshot.trade_date,
        "status": snapshot.status,
        "indices": _loads(snapshot.indices_json, []),
        "market_breadth": _loads(snapshot.market_breadth_json, {}),
        "turnover": _loads(snapshot.turnover_json, {}),
        "north_flow": _loads(snapshot.north_flow_json, {}),
        "news": _loads(snapshot.news_json, []),
        "created_at": snapshot.created_at,
    }

