#!/usr/bin/env python3
"""
AI分析CLI - 通过OpenCode执行大模型分析

用法:
    python cli_ai_analysis.py <trade_date> [step]
    
示例:
    python cli_ai_analysis.py 2025-04-10         # 执行全部步骤
    python cli_ai_analysis.py 2025-04-10 2    # 仅执行Step2
    python cli_ai_analysis.py 2025-04-10 3    # 仅执行Step3
"""
import sys
import json
import os
import subprocess
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import Database, AINews
from data.news_collector import collect_all_news
from data.sector_data import sector_data


def call_opencode(prompt: str) -> str:
    """调用OpenCode CLI执行分析"""
    try:
        result = subprocess.run(
            ["opencode", "chat", "--message", prompt],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout if result.returncode == 0 else f"ERROR: {result.stderr}"
    except FileNotFoundError:
        return "ERROR: opencode command not found"
    except subprocess.TimeoutExpired:
        return "ERROR: timeout after 120s"


def run_step2_ai_news(trade_date: str, db: Database) -> dict:
    """Step 2: AI新闻生成"""
    print(f"[CLI] Step 2: AI新闻生成 for {trade_date}")
    
    from data.market_data import MarketData
    market = MarketData()
    news = market.collect_news(limit=20)
    
    if not news:
        return {"step": 2, "status": "skipped", "reason": "no_raw_news"}
    
    news_text = "\n".join([
        f"{i+1}. {n.get('title','')[:80]} | {n.get('source','')}"
        for i, n in enumerate(news[:10])
    ])
    
    prompt = f"""你是一位专业的财经新闻分析师。请根据以下今日新闻，生成结构化摘要。

新闻:
{news_text}

请输出JSON数组格式:
[
  {{"title":"精简标题","summary":"50-100字简介+影响分析","category":"宏观/行业/公司/政策/国际/科技","sentiment":"positive/negative/neutral","keywords":["关键词1","关键词2"],"importance":8,"related_sectors":["板块1"]}}
]

只输出JSON，不要其他内容。"""

    result = call_opencode(prompt)
    
    try:
        structured = json.loads(result)
        if structured:
            from ai.news_generator import ai_news_generator
            ai_news_generator.save_to_db(trade_date, structured)
            print(f"[CLI] AI新闻生成完成: {len(structured)} 条")
            return {"step": 2, "status": "ok", "count": len(structured)}
    except json.JSONDecodeError:
        pass
    
    return {"step": 2, "status": "failed", "reason": "parse_error"}


def run_step3_ai_sector(trade_date: str, db: Database) -> dict:
    """Step 3: AI板块分析"""
    print(f"[CLI] Step 3: AI板块分析 for {trade_date}")
    
    ai_news_records = db.get_ai_news(trade_date)
    if not ai_news_records:
        return {"step": 3, "status": "skipped", "reason": "no_ai_news"}
    
    sector_list = sector_data.get_sector_list()
    sector_names = [s['name'] for s in sector_list[:30]] if sector_list else []
    
    news_text = "\n".join([
        f"{i+1}. {n.title[:60]} | {n.category} | {n.sentiment}"
        for i, n in enumerate(ai_news_records[:10])
    ])
    
    prompt = f"""你是一位专业的A股板块分析师。请基于今日新闻分析板块涨跌趋势。

新闻:
{news_text}

可选板块: {', '.join(sector_names[:20])}

输出JSON格式:
{{"sector_analysis":[{{"sector":"板块名","direction":"up/down/neutral","confidence":8,"score_up":75,"score_down":25,"reasons":["原因1"]}}],"market_overview":"整体观点30字","hot_sectors":["热点板块"]}}

只输出JSON。"""

    result = call_opencode(prompt)
    
    try:
        analysis = json.loads(result)
        if analysis.get('sector_analysis'):
            from ai.sector_analyzer import ai_sector_analyzer
            ai_sector_analyzer.save_to_db(trade_date, analysis)
            print(f"[CLI] AI板块分析完成: {len(analysis['sector_analysis'])} 个板块")
            return {"step": 3, "status": "ok", "count": len(analysis['sector_analysis'])}
    except json.JSONDecodeError:
        pass
    
    return {"step": 3, "status": "failed", "reason": "parse_error"}


def main():
    if len(sys.argv) < 2:
        print("用法: python cli_ai_analysis.py <trade_date> [step]")
        sys.exit(1)
    
    trade_date = sys.argv[1]
    step = sys.argv[2] if len(sys.argv) > 2 else None
    
    if trade_date == "today":
        from pipeline import get_trading_date
        trade_date, _ = get_trading_date()
    
    db = Database()
    results = []
    
    if step is None or step == "2":
        results.append(run_step2_ai_news(trade_date, db))
    
    if step is None or step == "3":
        results.append(run_step3_ai_sector(trade_date, db))
    
    print("\n[RESULT]")
    print(json.dumps({"trade_date": trade_date, "results": results}, ensure_ascii=False))
    
    if any(r.get("status") == "failed" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()