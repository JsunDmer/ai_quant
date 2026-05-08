import json
from fastapi import APIRouter, HTTPException
from backend.data.db import db
from backend.data.market_data import market_data
from dataclasses import asdict

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

    def _to_number(v, default=0.0):
        try:
            if v is None:
                return default
            return float(v)
        except Exception:
            return default

    def _normalize_stock_code(raw: str) -> str:
        code = (raw or "").strip().upper()
        if not code:
            return ""
        if "." in code:
            return code
        if code.startswith(("6", "9")):
            return f"{code}.SH"
        return f"{code}.SZ"

    # 获取原始新闻
    raw_news = _loads(snapshot.news_json, [])
    
    # 尝试获取 AI 结构化新闻
    ai_news_records = db.get_ai_news(snapshot.trade_date)
    
    if ai_news_records:
        news_list = []
        # 建立 raw_news 的 url 和 title -> raw_news 映射字典，以便找回新闻时间和来源
        url_to_raw = {}
        title_to_raw = {}
        for n in raw_news:
            if isinstance(n, dict):
                if n.get("url"):
                    url_to_raw[n["url"]] = n
                if n.get("title"):
                    title_to_raw[n["title"]] = n

        for record in ai_news_records:
            d = asdict(record)
            # 还原数组结构
            d["keywords"] = _loads(d.pop("keywords_json", "[]"), [])
            d["related_sectors"] = _loads(d.pop("related_sectors_json", "[]"), [])
            
            # 先按 URL 匹配，再按标题精确匹配，最后按标题模糊匹配
            raw_match = url_to_raw.get(d.get("source_url", ""))
            if not raw_match:
                raw_match = title_to_raw.get(d.get("title", ""))
            if not raw_match:
                # 模糊匹配
                for t, n in title_to_raw.items():
                    title_val = d.get("title", "")
                    if title_val and t and (title_val in t or t in title_val):
                        raw_match = n
                        break
            if not raw_match:
                raw_match = {}
                
            # 补充时间信息
            d["time"] = raw_match.get("time", "") or d.get("created_at", "")
            # 补充来源信息
            d["source"] = raw_match.get("source", "AI Agent")
            news_list.append(d)
    else:
        news_list = raw_news

    snapshot_north_flow = _loads(snapshot.north_flow_json, {})
    live_north_flow = market_data.get_north_flow()
    live_has_value = (
        abs(_to_number(live_north_flow.get("north"))) > 0
        or abs(_to_number(live_north_flow.get("south"))) > 0
        or abs(_to_number(live_north_flow.get("north_money"))) > 0
        or abs(_to_number(live_north_flow.get("south_money"))) > 0
    ) if isinstance(live_north_flow, dict) else False
    north_flow = {**snapshot_north_flow, **live_north_flow} if live_has_value else (snapshot_north_flow or live_north_flow)

    watchlist_codes = []
    seen = set()
    for row in db.get_latest_stock_signals(limit=120):
        code = _normalize_stock_code(getattr(row, "stock_code", ""))
        if code and code not in seen:
            seen.add(code)
            watchlist_codes.append(code)
    for stock in db.get_all_stocks():
        code = _normalize_stock_code(getattr(stock, "stock_code", ""))
        if code and code not in seen:
            seen.add(code)
            watchlist_codes.append(code)
    if not watchlist_codes:
        # 没有持仓和信号时使用一组大盘代表股，避免实时异动模块完全空白
        watchlist_codes = [
            "600519.SH",  # 贵州茅台
            "601318.SH",  # 中国平安
            "600036.SH",  # 招商银行
            "000001.SZ",  # 平安银行
            "000333.SZ",  # 美的集团
            "002594.SZ",  # 比亚迪
            "300750.SZ",  # 宁德时代
            "688981.SH",  # 中芯国际
        ]
    market_movers = market_data.get_realtime_movers(watchlist_codes, limit=10)

    return {
        "trade_date": snapshot.trade_date,
        "status": snapshot.status,
        "indices": _loads(snapshot.indices_json, []),
        "market_breadth": _loads(snapshot.market_breadth_json, {}),
        "turnover": _loads(snapshot.turnover_json, {}),
        "north_flow": north_flow,
        "market_movers": market_movers,
        "watchlist_size": len(watchlist_codes),
        "news": news_list,
        "created_at": snapshot.created_at,
    }

