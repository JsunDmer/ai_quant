import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Query

from backend.data.db import db
from backend.data.stock_data import stock_data


router = APIRouter(prefix="/api/signals", tags=["signals"])
_LATEST_CACHE: dict[str, dict] = {}
_LATEST_CACHE_TTL_SECONDS = 5


@router.get("/stock/{stock_code}/kline")
def get_stock_kline(stock_code: str, days: int = Query(default=60, ge=1, le=365)):
    """获取个股K线数据"""
    df = stock_data.get_kline_data(stock_code, days)
    if df.empty:
        return {"stock_code": stock_code, "data": []}
    records = df.to_dict(orient="records")
    return {
        "stock_code": stock_code,
        "data": [
            {
                "date": str(r.get("date", "")),
                "open": float(r.get("open", 0)),
                "high": float(r.get("high", 0)),
                "low": float(r.get("low", 0)),
                "close": float(r.get("close", 0)),
                "volume": int(r.get("volume", 0)),
            }
            for r in records
        ],
    }


@router.get("/stock/{stock_code}/financial")
def get_stock_financial(stock_code: str):
    """获取个股最新财务数据"""
    result = stock_data.is_stock_has_recent_performance(stock_code)
    return {
        "stock_code": stock_code,
        "has_data": result.get("has_financial_data", False),
        "net_profit": round(result.get("net_profit", 0) / 1e8, 2) if result.get("net_profit") else 0,
        "net_profit_yoy": round(result.get("net_profit_yoy", 0), 2),
        "roe": round(result.get("roe", 0), 2),
        "reason": result.get("reason", ""),
    }


@router.get("/latest")
def get_latest_signals(
    limit: int = Query(default=200, ge=1, le=1000),
    signal: str | None = None,
    include_realtime: bool = Query(default=False),
    include_auction: bool = Query(default=False),
):
    cache_key = f"{limit}:{signal or ''}:{int(include_realtime)}:{int(include_auction)}"
    cache_hit = _LATEST_CACHE.get(cache_key)
    now = time.time()
    if cache_hit and (now - float(cache_hit.get("ts", 0))) <= _LATEST_CACHE_TTL_SECONDS:
        return cache_hit["value"]

    rows = db.get_latest_stock_signals(signal=signal, limit=limit)

    def _loads(s, default):
        try:
            return json.loads(s) if s else default
        except Exception:
            return default

    def _normalize_plain_code(raw: str) -> str:
        code = (raw or "").strip().upper()
        if not code:
            return ""
        if "." in code:
            return code.split(".", 1)[0]
        return code

    def _auction_tag(auction: dict) -> str:
        if not auction or not auction.get("has_data"):
            return "无竞价数据"
        if stock_data.is_open_auction_weak(auction):
            return "竞价偏弱"
        pct = float(auction.get("pct_change", 0) or 0)
        vol_ratio = float(auction.get("volume_ratio", 0) or 0)
        if pct >= 1 and vol_ratio >= 0.8:
            return "竞价偏强"
        if pct > 0:
            return "竞价偏多"
        return "竞价中性"

    plain_codes = []
    seen_codes = set()
    for r in rows:
        plain = _normalize_plain_code(str(getattr(r, "stock_code", "")))
        if plain and plain not in seen_codes:
            seen_codes.add(plain)
            plain_codes.append(plain)

    in_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    should_fetch_realtime = include_realtime and (not in_test)
    quotes = stock_data.get_batch_quotes(plain_codes) if (plain_codes and should_fetch_realtime) else []
    quote_map = {str(q.get("code", "")).strip(): q for q in quotes}

    auction_map: dict[str, dict] = {}
    should_fetch_auction = include_auction and (not in_test)
    if should_fetch_auction:
        # 并发获取竞价，避免逐只串行导致接口阻塞
        with ThreadPoolExecutor(max_workers=5) as pool:
            future_map = {pool.submit(stock_data.get_open_auction_snapshot, code): code for code in plain_codes[:20]}
            for f in as_completed(future_map):
                code = future_map[f]
                try:
                    auction_map[code] = f.result(timeout=0.8)
                except Exception:
                    auction_map[code] = {}

    items = []
    for r in rows:
        stock_code = str(r.stock_code)
        plain_code = _normalize_plain_code(stock_code)
        quote = quote_map.get(plain_code, {})
        auction = auction_map.get(plain_code, {})
        items.append(
            {
                "trade_date": r.trade_date,
                "stock_code": stock_code,
                "stock_name": r.stock_name,
                "sector_name": r.sector_name,
                "signal": r.signal,
                "confidence": r.confidence,
                "factors": _loads(r.factors_json, []),
                "realtime": {
                    "price": quote.get("price", 0),
                    "pre_close": quote.get("pre_close", 0),
                    "change_percent": quote.get("change_percent", 0),
                    "change_amount": quote.get("change_amount", 0),
                    "source": "stock_data.get_batch_quotes" if quote else "none",
                },
                "auction": {
                    "has_data": bool(auction.get("has_data")) if auction else False,
                    "tag": _auction_tag(auction),
                    "pct_change": auction.get("pct_change", 0) if auction else 0,
                    "volume_ratio": auction.get("volume_ratio", 0) if auction else 0,
                    "trade_date": auction.get("trade_date", "") if auction else "",
                    "source": auction.get("source", "none") if auction else "none",
                },
                "created_at": r.created_at,
            }
        )

    trade_date = items[0]["trade_date"] if items else None
    payload = {"trade_date": trade_date, "items": items}
    _LATEST_CACHE[cache_key] = {"ts": now, "value": payload}
    return payload

