"""
收盘后流水线模块 - 后盘 Pipeline 编排

功能:
- 市场快照采集
- AI新闻生成
- AI板块分析
- 板块评分与推荐
- 数据持久化存储

CLI 用法:
    python -m pipeline run-post-close --date 2024-01-15
    python -m pipeline run-post-close  # 使用当天或最近交易日
"""
import json
import click
import importlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from data import akshare_patch
akshare_patch.patch()

from data.market_data import MarketData
from data.sector_data import SectorData

from db import Database, MarketSnapshot, SectorRecommendation, AINews, AISectorAnalysis, SectorDailyPerformance


# 交易日判断：简单排除周末
def get_trading_date(date_str: Optional[str] = None) -> tuple[str, str]:
    """
    获取交易日期（处理非交易日自动回退）
    
    Returns:
        (trade_date, data_date): 实际使用的交易日期, 数据对应的日期
    """
    if date_str:
        target = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        target = datetime.now()
    
    try:
        ecals = importlib.import_module("exchange_calendars")
        calendar = ecals.get_calendar("XSHG")
        target_day = target.date()
        if calendar.is_session(target_day):
            return target.strftime('%Y-%m-%d'), target.strftime('%Y-%m-%d')
        sessions = calendar.sessions_in_range(
            (target - timedelta(days=30)).date(), target_day
        )
        if len(sessions) > 0:
            last_session = sessions[-1]
            return last_session.strftime('%Y-%m-%d'), target.strftime('%Y-%m-%d')
    except Exception:
        pass

    # 兜底：排除周末
    for i in range(7):
        check_date = target - timedelta(days=i)
        if check_date.weekday() < 5:
            return check_date.strftime('%Y-%m-%d'), target.strftime('%Y-%m-%d')
    
    # 兜底：返回输入日期
    return target.strftime('%Y-%m-%d'), target.strftime('%Y-%m-%d')


def run_post_close_pipeline(trade_date: Optional[str] = None, enabled_sources: Optional[List[str]] = None, ai_enabled: bool = True, refresh_realtime_only: bool = False) -> Dict[str, Any]:
    """
    执行收盘后流水线

    Args:
        trade_date: 指定交易日期，None 则自动获取最近交易日
        enabled_sources: 启用的新闻源列表，None 表示全部启用
        ai_enabled: 是否启用AI分析（新闻生成+板块分析）
        refresh_realtime_only: 仅更新实时数据模式。当天已搜索过新闻后，
                              设为True可跳过新闻搜索和板块分析，只更新市场快照、个股数据

    Returns:
        dict with status, trade_date, data_date, market_snapshot,
               sector_recommendations, stock_signals
    """
    # Step 1: 确定交易日期
    trade_date, data_date = get_trading_date(trade_date)
    print(f"[Pipeline] 交易日期: {trade_date}, 数据日期: {data_date}")
    
    # 初始化结果容器
    result: Dict[str, Any] = {
        'status': 'ok',
        'trade_date': trade_date,
        'data_date': data_date,
        'market_snapshot': None,
        'sector_recommendations': [],
        'stock_signals': [],
        'dashboard_report': {},
        'errors': []
    }
    
    # 初始化模块
    market = MarketData()
    sector = SectorData()
    db = Database()
    
    # Step 1: 市场快照采集
    print("[Pipeline Step 1/3] 采集市场快照...")
    try:
        snapshot = market.collect_post_close_snapshot(trade_date, enabled_sources=enabled_sources or [])
        result['market_snapshot'] = snapshot
        
        # 保存到数据库
        db_snapshot = MarketSnapshot(
            trade_date=trade_date,
            indices_json=json.dumps(snapshot.get('indices', [])),
            market_breadth_json=json.dumps(snapshot.get('market_breadth', {})),
            turnover_json=json.dumps(snapshot.get('turnover', {})),
            north_flow_json=json.dumps(snapshot.get('north_flow', {})),
            news_json=json.dumps(snapshot.get('news', [])),
            status=snapshot.get('status', 'completed')
        )
        db.upsert_market_snapshot(db_snapshot)
        print(f"[Pipeline] 市场快照已保存，状态: {snapshot.get('status', 'unknown')}")
        
        if snapshot.get('status') == 'degraded':
            result['errors'].append('market_snapshot: degraded')
            result['status'] = 'degraded'
            
    except Exception as e:
        result['errors'].append(f'market_snapshot: {str(e)}')
        result['status'] = 'degraded'
        print(f"[Pipeline] 市场快照采集失败: {e}")
    
    # Step 1.5: 记录板块当日涨跌幅（不依赖 AI，始终执行）
    sector_list = []
    print("[Pipeline Step 1.5] 记录板块实际涨跌幅...")
    try:
        sector_list = sector.get_sector_list()
        perfs = []
        for s in sector_list:
            perfs.append(SectorDailyPerformance(
                trade_date=trade_date,
                sector_name=s['name'],
                change_pct=s['change'],
                stock_count=s.get('stock_count', 0)
            ))
        if perfs:
            db.batch_upsert_sector_daily_performance(perfs)
            print(f"[Pipeline] 板块涨跌幅已记录，共 {len(perfs)} 个板块")
    except Exception as e:
        result['errors'].append(f'sector_performance: {str(e)}')
        print(f"[Pipeline] 板块涨跌幅记录失败: {e}")

    # Step 2: AI新闻生成
    structured_news = []
    if refresh_realtime_only:
        print("[Pipeline Step 2/3] 仅更新实时数据模式，跳过AI新闻生成")
    elif not ai_enabled:
        print("[Pipeline Step 2/3] AI分析已关闭，跳过AI新闻生成")
    else:
        print("[Pipeline Step 2/3] AI新闻生成...")
        try:
            # 获取原始新闻
            news = []
            try:
                snapshot = result.get('market_snapshot')
                if snapshot:
                    news = snapshot.get('news', [])
            except:
                pass

            if news:
                from ai.news_generator import ai_news_generator

                # 生成结构化新闻
                structured_news = ai_news_generator.generate_structured_news(news)

                if structured_news:
                    # 保存到数据库
                    ai_news_generator.save_to_db(trade_date, structured_news)
                    print(f"[Pipeline] AI新闻已生成，共 {len(structured_news)} 条")
                else:
                    print("[Pipeline] AI新闻生成返回空结果")
            else:
                print("[Pipeline] 无原始新闻，跳过AI新闻生成")

        except Exception as e:
            result['errors'].append(f'ai_news_generation: {str(e)}')
            print(f"[Pipeline] AI新闻生成失败: {e}")

    # Step 3: AI板块分析
    if refresh_realtime_only:
        print("[Pipeline Step 3/3] 仅更新实时数据模式，跳过AI板块分析")
    elif not ai_enabled:
        print("[Pipeline Step 3/3] AI分析已关闭，跳过AI板块分析")
    else:
        print("[Pipeline Step 3/3] AI板块分析...")
        try:
            # 从数据库获取AI生成的新闻
            ai_news_records = db.get_ai_news(trade_date)

            if ai_news_records:
                # 转换为dict格式
                ai_news_list = []
                for news in ai_news_records:
                    ai_news_list.append({
                        'title': news.title,
                        'summary': news.summary,
                        'category': news.category,
                        'sentiment': news.sentiment,
                        'keywords_json': news.keywords_json,
                        'related_sectors_json': news.related_sectors_json
                    })

                # 调用AI板块分析（传入板块名列表，确保AI只从真实板块中选择）
                from ai.sector_analyzer import ai_sector_analyzer
                sector_names = [s['name'] for s in sector_list] if sector_list else []
                sector_analysis = ai_sector_analyzer.analyze_sectors(ai_news_list, sector_names=sector_names)

                if sector_analysis.get('sector_analysis'):
                    ai_sector_analyzer.save_to_db(trade_date, sector_analysis)
                    print(f"[Pipeline] AI板块分析完成，分析了 {len(sector_analysis['sector_analysis'])} 个板块")
                else:
                    print("[Pipeline] AI板块分析返回空结果")
            else:
                print("[Pipeline] 无AI新闻数据，跳过AI板块分析")

        except Exception as e:
            result['errors'].append(f'ai_sector_analysis: {str(e)}')
            print(f"[Pipeline] AI板块分析失败: {e}")
    
    # Step 3: 板块评分与推荐
    print("[Pipeline Step 3/3] 板块评分与推荐...")
    try:
        sector_results = sector.recommend_sectors()
        
        # 展平并保存推荐结果
        all_recommendations = []
        for bucket, recommendations in sector_results.items():
            for rec in recommendations:
                all_recommendations.append({
                    'sector_name': rec['sector_name'],
                    'score': rec['score'],
                    'bucket': rec['bucket'],
                    'reasons': rec['reasons']
                })
                
                # 保存到数据库
                db_rec = SectorRecommendation(
                    trade_date=trade_date,
                    sector_name=rec['sector_name'],
                    score=rec['score'],
                    bucket=rec['bucket'],
                    reasons_json=json.dumps(rec['reasons'])
                )
                db.upsert_sector_recommendation(db_rec)
        
        result['sector_recommendations'] = all_recommendations
        print(f"[Pipeline] 板块推荐已保存，共 {len(all_recommendations)} 个")
        
    except Exception as e:
        result['errors'].append(f'sector_scoring: {str(e)}')
        result['status'] = 'degraded'
        print(f"[Pipeline] 板块评分失败: {e}")

    summary = {
        "sectors": len(result.get('sector_recommendations', [])),
        "signals": len(result.get('stock_signals', [])),
        "status": result.get('status'),
    }
    result['dashboard_report'] = {
        "headline": f"交易日 {trade_date} 分析完成",
        "summary": summary,
        "action_points": [],
        "risk_alerts": result.get('errors', []),
        "checklist": [],
    }

    # 完成
    print(f"[Pipeline] 流水线完成，状态: {result['status']}")
    if result['errors']:
        print(f"[Pipeline] 错误: {result['errors']}")

    return result


# CLI 入口
@click.group()
def cli():
    """收盘后流水线 CLI"""
    pass


@cli.command('run-post-close')
@click.option('--date', '-d', help='交易日期 (YYYY-MM-DD)，默认自动获取最近交易日')
def run_post_close_cli(date: Optional[str]):
    """执行收盘后流水线"""
    click.echo(f"开始执行收盘后流水线，指定日期: {date or '自动'}")
    result = run_post_close_pipeline(date)
    
    click.echo(f"\n===== 执行结果 =====")
    click.echo(f"状态: {result['status']}")
    click.echo(f"交易日期: {result['trade_date']}")
    click.echo(f"数据日期: {result['data_date']}")
    
    market = result.get('market_snapshot', {})
    if market:
        click.echo(f"\n市场快照:")
        click.echo(f"  - 指数数量: {len(market.get('indices', []))}")
        breadth = market.get('market_breadth', {})
        if breadth:
            click.echo(f"  - 上涨: {breadth.get('up', 0)}, 下跌: {breadth.get('down', 0)}")
    
    click.echo(f"\n板块推荐: {len(result.get('sector_recommendations', []))} 个")
    click.echo(f"股票信号: {len(result.get('stock_signals', []))} 个")
    
    if result['errors']:
        click.echo(f"\n⚠️ 错误信息:")
        for err in result['errors']:
            click.echo(f"  - {err}")

    report = result.get('dashboard_report', {})
    if report:
        click.echo("\n===== 决策仪表盘 =====")
        click.echo(f"结论: {report.get('headline', '')}")
        summary = report.get('summary', {})
        if summary:
            click.echo(f"摘要: {summary}")
    
    if result['status'] == 'ok':
        click.echo("\n✅ 流水线执行成功")
    else:
        click.echo("\n⚠️ 流水线执行完成（降级模式）")


if __name__ == '__main__':
    cli()
