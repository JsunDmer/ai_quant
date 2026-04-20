import json

from fastapi import APIRouter

from db import db


router = APIRouter(prefix="/api/sectors", tags=["sectors"])


@router.get("/latest")
def get_latest_sectors():
    ai_sector_analysis = db.get_latest_ai_sector_analysis()
    sector_recs = db.get_latest_sector_recommendations()

    # build map for rec reasons and scores
    score_map = {r.sector_name: r.score for r in sector_recs} if sector_recs else {}
    reasons_map = {}
    if sector_recs:
        for r in sector_recs:
            reasons = []
            try:
                if r.reasons_json:
                    rr = json.loads(r.reasons_json)
                    if isinstance(rr, list):
                        reasons = rr
                    elif isinstance(rr, dict):
                        reasons = rr.get("reasons", rr.get("推荐理由", [])) or []
            except Exception:
                reasons = []
            reasons_map[r.sector_name] = reasons

    items = []
    if ai_sector_analysis:
        for s in ai_sector_analysis:
            reasons = []
            try:
                if s.reasons_json:
                    rr = json.loads(s.reasons_json)
                    reasons = rr if isinstance(rr, list) else []
            except Exception:
                reasons = []
            if not reasons:
                reasons = reasons_map.get(s.sector_name, [])

            items.append(
                {
                    "trade_date": s.trade_date,
                    "sector_name": s.sector_name,
                    "direction": s.direction,
                    "confidence": getattr(s, "confidence", 0),
                    "score_up": getattr(s, "score_up", 0),
                    "score_down": getattr(s, "score_down", 0),
                    "rec_score": score_map.get(s.sector_name, 0),
                    "reasons": reasons,
                }
            )
    else:
        # fallback: return recs only
        for r in sector_recs:
            items.append(
                {
                    "trade_date": r.trade_date,
                    "sector_name": r.sector_name,
                    "direction": None,
                    "confidence": None,
                    "score_up": None,
                    "score_down": None,
                    "rec_score": r.score,
                    "reasons": reasons_map.get(r.sector_name, []),
                }
            )

    # best-effort: derive latest trade_date
    trade_date = None
    if items:
        trade_date = items[0].get("trade_date")

    return {"trade_date": trade_date, "items": items}

