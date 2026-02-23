"""
数据库操作模块
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from config import config


@dataclass
class FollowedStock:
    """关注的股票"""
    stock_code: str          # 股票代码 (如: 600519)
    stock_name: str          # 股票名称
    cost_price: float = 0.0  # 成本价
    volume: int = 0          # 持仓数量
    alarm_percent: float = 3.0  # 报警涨跌幅
    alarm_price: float = 0.0    # 报警价格
    created_at: str = ""     # 创建时间
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class AnalysisRecord:
    """AI 分析记录"""
    id: int
    stock_code: str
    stock_name: str
    question: str
    answer: str
    created_at: str


@dataclass
class AlertRecord:
    """报警记录"""
    id: int
    stock_code: str
    stock_name: str
    alert_type: str      # "up" or "down"
    price: float
    change_percent: float
    message: str
    created_at: str



@dataclass
class MarketSnapshot:
    """市场快照数据"""
    trade_date: str           # 交易日期 (如: 2024-01-15)
    indices_json: str         # 指数数据 JSON
    market_breadth_json: str  # 市场广度 JSON
    turnover_json: str        # 成交额 JSON
    north_flow_json: str      # 北向资金 JSON
    news_json: str            # 新闻热点 JSON
    status: str = "pending"  # 状态: pending/completed
    created_at: str = ""     # 创建时间
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class SectorRecommendation:
    trade_date: str = ""
    sector_name: str = ""
    score: float = 0.0
    bucket: str = ""
    reasons_json: str = ""
    created_at: str = ""
    id: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class StockSignal:
    trade_date: str = ""
    stock_code: str = ""
    stock_name: str = ""
    sector_name: str = ""
    signal: str = ""
    confidence: float = 0.0
    factors_json: str = ""
    created_at: str = ""
    id: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")



@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    trade_date: str = ""
    market_view: str = ""
    key_insight: str = ""
    hot_keywords_json: str = ""
    sector_analysis_json: str = ""
    news_sources_json: str = ""  # 使用的新闻源配置
    status: str = "pending"  # pending/running/completed/failed
    created_at: str = ""
    id: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class AINews:
    """AI新闻数据"""
    trade_date: str = ""
    title: str = ""
    summary: str = ""
    category: str = ""
    sentiment: str = ""
    keywords_json: str = ""
    source_url: str = ""
    importance: int = 5
    related_sectors_json: str = ""
    created_at: str = ""
    id: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@dataclass
class AISectorAnalysis:
    """AI板块分析"""

    trade_date: str = ""
    sector_name: str = ""
    direction: str = ""  # up/down/neutral
    confidence: int = 0
    score_up: int = 50
    score_down: int = 50
    reasons_json: str = ""
    related_news_json: str = ""
    created_at: str = ""
    id: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class SectorStock:
    """板块成分股缓存"""
    sector_name: str = ""
    stock_code: str = ""
    stock_name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    trade_date: str = ""
    created_at: str = ""
    id: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Database:
    """数据库管理"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            # 关注股票表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS followed_stocks (
                    stock_code TEXT PRIMARY KEY,
                    stock_name TEXT NOT NULL,
                    cost_price REAL DEFAULT 0,
                    volume INTEGER DEFAULT 0,
                    alarm_percent REAL DEFAULT 3.0,
                    alarm_price REAL DEFAULT 0,
                    created_at TEXT
                )
            """)
            
            # AI 分析记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    question TEXT,
                    answer TEXT,
                    created_at TEXT
                )
            """)
            
            # 报警记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    alert_type TEXT,
                    price REAL,
                    change_percent REAL,
                    message TEXT,
                    created_at TEXT
                )
            """)

            
            # 市场快照表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_snapshots (
                    trade_date TEXT PRIMARY KEY,
                    indices_json TEXT,
                    market_breadth_json TEXT,
                    turnover_json TEXT,
                    north_flow_json TEXT,
                    news_json TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT
                )
            """)
            
            # 行业推荐表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sector_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT NOT NULL,
                    sector_name TEXT NOT NULL,
                    score REAL,
                    bucket TEXT,
                    reasons_json TEXT,
                    created_at TEXT,
                    UNIQUE(trade_date, sector_name)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sector_rec_date 
                ON sector_recommendations(trade_date)
            """)
            
            # 股票信号表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    sector_name TEXT,
                    signal TEXT,
                    confidence REAL,
                    factors_json TEXT,
                    created_at TEXT,
                    UNIQUE(trade_date, stock_code)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_signals_date 
                ON stock_signals(trade_date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_signals_code 
                ON stock_signals(stock_code)
            """)

            # AI分析结果表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT NOT NULL,
                    market_view TEXT,
                    key_insight TEXT,
                    hot_keywords_json TEXT,
                    sector_analysis_json TEXT,
                    news_sources_json TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    UNIQUE(trade_date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_date
                ON ai_analysis_results(trade_date)
            """)
            
            # AI新闻表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    category TEXT,
                    sentiment TEXT,
                    keywords_json TEXT,
                    source_url TEXT,
                    importance INTEGER DEFAULT 5,
                    related_sectors_json TEXT,
                    created_at TEXT,
                    UNIQUE(trade_date, title)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_news_date 
                ON ai_news(trade_date)
            """)
            
            # AI板块分析表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_sector_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT NOT NULL,
                    sector_name TEXT NOT NULL,
                    direction TEXT,
                    confidence INTEGER,
                    score_up INTEGER,
                    score_down INTEGER,
                    reasons_json TEXT,
                    related_news_json TEXT,
                    created_at TEXT,
                    UNIQUE(trade_date, sector_name)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_sector_date
                ON ai_sector_analysis(trade_date)
            """)

            # 板块成分股缓存表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sector_stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sector_name TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    price REAL DEFAULT 0,
                    change_pct REAL DEFAULT 0,
                    trade_date TEXT NOT NULL,
                    created_at TEXT,
                    UNIQUE(sector_name, stock_code, trade_date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sector_stocks_sector
                ON sector_stocks(sector_name, trade_date)
            """)

            conn.commit()
    
    # ========== 关注股票操作 ==========
    
    def add_stock(self, stock: FollowedStock) -> bool:
        """添加关注股票"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO followed_stocks 
                    (stock_code, stock_name, cost_price, volume, alarm_percent, alarm_price, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    stock.stock_code, stock.stock_name, stock.cost_price,
                    stock.volume, stock.alarm_percent, stock.alarm_price, stock.created_at
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"添加股票失败: {e}")
                return False
    
    def remove_stock(self, stock_code: str) -> bool:
        """取消关注股票"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM followed_stocks WHERE stock_code = ?", (stock_code,))
            conn.commit()
            return True
    
    def get_all_stocks(self) -> List[FollowedStock]:
        """获取所有关注的股票"""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM followed_stocks ORDER BY created_at DESC").fetchall()
            return [FollowedStock(**dict(row)) for row in rows]
    
    def get_stock(self, stock_code: str) -> Optional[FollowedStock]:
        """获取单个股票"""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM followed_stocks WHERE stock_code = ?", (stock_code,)).fetchone()
            return FollowedStock(**dict(row)) if row else None
    
    def update_stock(self, stock: FollowedStock) -> bool:
        """更新股票信息"""
        return self.add_stock(stock)
    
    # ========== 分析记录操作 ==========
    
    def save_analysis(self, stock_code: str, stock_name: str, question: str, answer: str) -> Optional[int]:
        """保存 AI 分析记录"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO analysis_records (stock_code, stock_name, question, answer, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (stock_code, stock_name, question, answer, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return cursor.lastrowid
    
    def get_analysis_history(self, stock_code: Optional[str] = None, limit: int = 20) -> List[AnalysisRecord]:
        """获取分析历史"""
        with self.get_connection() as conn:
            if stock_code:
                rows = conn.execute(
                    "SELECT * FROM analysis_records WHERE stock_code = ? ORDER BY created_at DESC LIMIT ?",
                    (stock_code, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM analysis_records ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [AnalysisRecord(**dict(row)) for row in rows]
    
    # ========== 报警记录操作 ==========
    
    def save_alert(self, stock_code: str, stock_name: str, alert_type: str, 
                   price: float, change_percent: float, message: str) -> Optional[int]:
        """保存报警记录"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO alert_records 
                (stock_code, stock_name, alert_type, price, change_percent, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (stock_code, stock_name, alert_type, price, change_percent, message, 
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return cursor.lastrowid
    
    def get_alert_history(self, limit: int = 50) -> List[AlertRecord]:
        """获取报警历史"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM alert_records ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [AlertRecord(**dict(row)) for row in rows]


    # ========== 市场快照操作 ==========
    
    def upsert_market_snapshot(self, snapshot: MarketSnapshot) -> bool:
        """更新或插入市场快照"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO market_snapshots 
                    (trade_date, indices_json, market_breadth_json, turnover_json, 
                     north_flow_json, news_json, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.trade_date, snapshot.indices_json, snapshot.market_breadth_json,
                    snapshot.turnover_json, snapshot.north_flow_json, snapshot.news_json,
                    snapshot.status, snapshot.created_at
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"保存市场快照失败: {e}")
                return False
    
    def get_market_snapshot(self, trade_date: str) -> Optional[MarketSnapshot]:
        """获取指定日期的市场快照"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM market_snapshots WHERE trade_date = ?", 
                (trade_date,)
            ).fetchone()
            return MarketSnapshot(**dict(row)) if row else None
    
    def get_latest_market_snapshot(self) -> Optional[MarketSnapshot]:
        """获取最新的市场快照"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM market_snapshots ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            return MarketSnapshot(**dict(row)) if row else None
    
    # ========== 行业推荐操作 ==========
    
    def upsert_sector_recommendation(self, rec: SectorRecommendation) -> bool:
        """更新或插入行业推荐"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO sector_recommendations 
                    (trade_date, sector_name, score, bucket, reasons_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rec.trade_date, rec.sector_name, rec.score, 
                    rec.bucket, rec.reasons_json, rec.created_at
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"保存行业推荐失败: {e}")
                return False
    
    def get_sector_recommendations(self, trade_date: str) -> List[SectorRecommendation]:
        """获取指定日期的行业推荐"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sector_recommendations WHERE trade_date = ? ORDER BY score DESC",
                (trade_date,)
            ).fetchall()
            return [SectorRecommendation(**dict(row)) for row in rows]
    
    def get_latest_sector_recommendations(self) -> List[SectorRecommendation]:
        """获取最新的行业推荐"""
        with self.get_connection() as conn:
            latest_date_row = conn.execute(
                "SELECT MAX(trade_date) as latest FROM sector_recommendations"
            ).fetchone()
            if not latest_date_row or not latest_date_row['latest']:
                return []
            latest_date = latest_date_row['latest']
            rows = conn.execute(
                "SELECT * FROM sector_recommendations WHERE trade_date = ? ORDER BY score DESC",
                (latest_date,)
            ).fetchall()
            return [SectorRecommendation(**dict(row)) for row in rows]
    
    # ========== 股票信号操作 ==========
    
    def upsert_stock_signal(self, signal: StockSignal) -> bool:
        """更新或插入股票信号"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_signals 
                    (trade_date, stock_code, stock_name, sector_name, signal, confidence, factors_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal.trade_date, signal.stock_code, signal.stock_name,
                    signal.sector_name, signal.signal, signal.confidence,
                    signal.factors_json, signal.created_at
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"保存股票信号失败: {e}")
                return False
    
    def get_stock_signals(self, trade_date: str) -> List[StockSignal]:
        """获取指定日期的股票信号"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM stock_signals WHERE trade_date = ? ORDER BY confidence DESC",
                (trade_date,)
            ).fetchall()
            return [StockSignal(**dict(row)) for row in rows]
    
    def get_stock_signal(self, trade_date: str, stock_code: str) -> Optional[StockSignal]:
        """获取指定日期和股票的信号"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM stock_signals WHERE trade_date = ? AND stock_code = ?",
                (trade_date, stock_code)
            ).fetchone()
            return StockSignal(**dict(row)) if row else None
    
    def get_latest_stock_signals(self, signal: Optional[str] = None, limit: int = 50) -> List[StockSignal]:
        """获取最新的股票信号"""
        with self.get_connection() as conn:
            if signal:
                rows = conn.execute(
                    "SELECT * FROM stock_signals WHERE signal = ? ORDER BY trade_date DESC, confidence DESC LIMIT ?",
                    (signal, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM stock_signals ORDER BY trade_date DESC, confidence DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [StockSignal(**dict(row)) for row in rows]


    # ========== AI分析结果操作 ==========
    
    def upsert_ai_analysis_result(self, result: AIAnalysisResult) -> bool:
        """更新或插入AI分析结果"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO ai_analysis_results 
                    (trade_date, market_view, key_insight, hot_keywords_json, 
                     sector_analysis_json, news_sources_json, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.trade_date, result.market_view, result.key_insight,
                    result.hot_keywords_json, result.sector_analysis_json,
                    result.news_sources_json, result.status, result.created_at
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"保存AI分析结果失败: {e}")
                return False
    
    def get_ai_analysis_result(self, trade_date: str) -> Optional[AIAnalysisResult]:
        """获取指定日期的AI分析结果"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ai_analysis_results WHERE trade_date = ?", 
                (trade_date,)
            ).fetchone()
            return AIAnalysisResult(**dict(row)) if row else None
    
    def get_latest_ai_analysis_result(self) -> Optional[AIAnalysisResult]:
        """获取最新的AI分析结果"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ai_analysis_results ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            return AIAnalysisResult(**dict(row)) if row else None
    
    # ========== AI新闻操作 ==========
    
    def upsert_ai_news(self, news: AINews) -> bool:
        """保存AI新闻"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO ai_news 
                    (trade_date, title, summary, category, sentiment, keywords_json, source_url, importance, related_sectors_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    news.trade_date, news.title, news.summary, news.category, news.sentiment,
                    news.keywords_json, news.source_url, news.importance, news.related_sectors_json, news.created_at
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"保存AI新闻失败: {e}")
                return False
    
    def get_ai_news(self, trade_date: str) -> List[AINews]:
        """获取指定日期的AI新闻"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_news WHERE trade_date = ? ORDER BY importance DESC",
                (trade_date,)
            ).fetchall()
            return [AINews(**dict(row)) for row in rows]
    
    def get_latest_ai_news(self) -> List[AINews]:
        """获取最新的AI新闻"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT trade_date FROM ai_news ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            if row:
                return self.get_ai_news(row['trade_date'])
            return []

    # ========== AI板块分析操作 ==========
    
    def upsert_ai_sector_analysis(self, analysis: AISectorAnalysis) -> bool:
        """保存AI板块分析"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO ai_sector_analysis 
                    (trade_date, sector_name, direction, confidence, score_up, score_down, reasons_json, related_news_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis.trade_date, analysis.sector_name, analysis.direction, analysis.confidence,
                    analysis.score_up, analysis.score_down, analysis.reasons_json, analysis.related_news_json, analysis.created_at
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"保存AI板块分析失败: {e}")
                return False
    
    def get_ai_sector_analysis(self, trade_date: str) -> List[AISectorAnalysis]:
        """获取指定日期的AI板块分析"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_sector_analysis WHERE trade_date = ? ORDER BY confidence DESC",
                (trade_date,)
            ).fetchall()
            return [AISectorAnalysis(**dict(row)) for row in rows]
    
    def get_latest_ai_sector_analysis(self) -> List[AISectorAnalysis]:
        """获取最新的AI板块分析"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT trade_date FROM ai_sector_analysis ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            if row:
                return self.get_ai_sector_analysis(row['trade_date'])
            return []

    # ========== 板块成分股缓存操作 ==========

    def save_sector_stocks(self, sector_name: str, trade_date: str, stocks: List[dict]) -> bool:
        """批量保存板块成分股"""
        with self.get_connection() as conn:
            try:
                for s in stocks:
                    conn.execute("""
                        INSERT OR REPLACE INTO sector_stocks
                        (sector_name, stock_code, stock_name, price, change_pct, trade_date, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sector_name, s['code'], s['name'],
                        s.get('price', 0), s.get('change', 0),
                        trade_date, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                conn.commit()
                return True
            except Exception as e:
                print(f"保存板块成分股失败: {e}")
                return False

    def get_sector_stocks(self, sector_name: str, trade_date: str = None) -> List[SectorStock]:
        """获取板块成分股（指定日期或最新）"""
        with self.get_connection() as conn:
            if trade_date:
                rows = conn.execute(
                    "SELECT * FROM sector_stocks WHERE sector_name = ? AND trade_date = ? ORDER BY change_pct DESC",
                    (sector_name, trade_date)
                ).fetchall()
            else:
                # 取该板块最新一天的数据
                latest = conn.execute(
                    "SELECT trade_date FROM sector_stocks WHERE sector_name = ? ORDER BY trade_date DESC LIMIT 1",
                    (sector_name,)
                ).fetchone()
                if not latest:
                    return []
                rows = conn.execute(
                    "SELECT * FROM sector_stocks WHERE sector_name = ? AND trade_date = ? ORDER BY change_pct DESC",
                    (sector_name, latest['trade_date'])
                ).fetchall()
            return [SectorStock(**dict(row)) for row in rows]

    def get_sector_stocks_date(self, sector_name: str) -> str:
        """获取板块成分股的最新缓存日期"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT trade_date FROM sector_stocks WHERE sector_name = ? ORDER BY trade_date DESC LIMIT 1",
                (sector_name,)
            ).fetchone()
            return row['trade_date'] if row else ""

    def get_all_cached_sectors(self) -> List[str]:
        """获取所有有缓存的板块名称"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT sector_name FROM sector_stocks ORDER BY sector_name"
            ).fetchall()
            return [row['sector_name'] for row in rows]


# 全局数据库实例
db = Database()
