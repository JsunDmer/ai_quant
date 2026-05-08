import json
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter

from backend.data.db import db


router = APIRouter(prefix="/api/sectors", tags=["sectors"])


def _build_signal_stock_map(trade_date: str | None) -> Dict[str, List[Dict[str, Any]]]:
    if trade_date:
        rows = db.get_stock_signals(trade_date)
    else:
        rows = db.get_latest_stock_signals(limit=500)
    sector_map: Dict[str, List[Dict[str, Any]]] = {}
    dedupe: Dict[str, set[str]] = {}
    for row in rows:
        if row.signal not in ("buy", "strong_buy"):
            continue
        if not row.sector_name or not row.stock_code:
            continue
        if row.confidence is not None and row.confidence < 0.55:
            continue

        seen = dedupe.setdefault(row.sector_name, set())
        if row.stock_code in seen:
            continue
        seen.add(row.stock_code)

        label = "强买入" if row.signal == "strong_buy" else "买入"
        confidence_pct = int((row.confidence or 0) * 100)
        sector_map.setdefault(row.sector_name, []).append(
            {
                "code": row.stock_code,
                "name": row.stock_name,
                "signal": row.signal,
                "confidence": row.confidence,
                "reason": f"技术信号 {label}（置信度{confidence_pct}%）",
            }
        )
    return sector_map


def _build_top_stocks_from_cache(
    sector_name: str,
    trade_date: str | None,
    max_count: int = 5,
) -> Tuple[List[Dict[str, Any]], str]:
    cached = db.get_sector_stocks(sector_name, trade_date) if trade_date else []
    if not cached:
        cached = db.get_sector_stocks(sector_name)
    if not cached:
        return [], ""

    normalized: List[Dict[str, Any]] = []
    for row in cached:
        if row.price <= 0:
            continue
        normalized.append(
            {
                "code": row.stock_code,
                "name": row.stock_name,
                "price": row.price,
                "change": row.change_pct,
            }
        )
    if not normalized:
        return [], cached[0].trade_date

    positive = sorted(
        [s for s in normalized if float(s.get("change", 0) or 0) > 0],
        key=lambda s: float(s.get("change", 0) or 0),
        reverse=True,
    )
    non_positive = sorted(
        [s for s in normalized if float(s.get("change", 0) or 0) <= 0],
        key=lambda s: float(s.get("change", 0) or 0),
        reverse=True,
    )

    selected: List[Dict[str, Any]] = []
    selected_codes = set()
    for stock in positive:
        if len(selected) >= max_count:
            break
        selected.append(stock)
        selected_codes.add(stock["code"])

    min_count = min(3, max_count)
    if len(selected) < min_count:
        for stock in non_positive:
            if stock["code"] in selected_codes:
                continue
            selected.append(stock)
            selected_codes.add(stock["code"])
            if len(selected) >= min_count:
                break

    if len(selected) < max_count:
        for stock in non_positive:
            if stock["code"] in selected_codes:
                continue
            selected.append(stock)
            selected_codes.add(stock["code"])
            if len(selected) >= max_count:
                break

    top_stocks: List[Dict[str, Any]] = []
    for stock in selected:
        change = float(stock.get("change", 0) or 0)
        if change > 0:
            reason = f"板块内领涨{change:.1f}%"
        elif change < 0:
            reason = f"板块内相对抗跌{change:.1f}%"
        else:
            reason = "板块内相对稳健"
        top_stocks.append(
            {
                "code": stock["code"],
                "name": stock["name"],
                "price": stock["price"],
                "change": change,
                "reason": reason,
            }
        )
    return top_stocks, cached[0].trade_date


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

    signal_stock_map = _build_signal_stock_map(trade_date)
    for item in items:
        sector_name = item.get("sector_name", "")
        signal_stocks = signal_stock_map.get(sector_name, [])
        if signal_stocks:
            item["top_stocks"] = signal_stocks[:5]
            item["stocks_source"] = "signal"
            item["stocks_date"] = trade_date
            continue

        top_stocks, stocks_date = _build_top_stocks_from_cache(sector_name, trade_date, max_count=5)
        item["top_stocks"] = top_stocks
        item["stocks_source"] = "sector_cache" if top_stocks else "none"
        item["stocks_date"] = stocks_date

    return {"trade_date": trade_date, "items": items}

