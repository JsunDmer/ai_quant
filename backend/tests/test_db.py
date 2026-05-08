"""
Test module for database operations
"""
import pytest
import os
import sys
import tempfile


class TestDatabaseTables:
    def test_tables_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database
            db = Database(db_path)
            with db.get_connection() as conn:
                tables = [row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
            assert "market_snapshots" in tables
            assert "sector_recommendations" in tables
            assert "sector_stock_recommendations" in tables
            assert "recommendation_evaluations" in tables
            assert "stock_signals" in tables
            assert "followed_stocks" in tables
            assert "analysis_records" in tables
            assert "alert_records" in tables


class TestMarketSnapshot:
    def test_upsert_and_get_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, MarketSnapshot
            db = Database(db_path)
            snapshot = MarketSnapshot(
                trade_date="2024-01-15",
                indices_json='{"shanghai": {"price": 3000}}',
                market_breadth_json='{"上涨": 2000}',
                turnover_json='{"total": 100}',
                north_flow_json='{"net": 10}',
                news_json='[{"title": "Test"}]',
                status="completed"
            )
            result = db.upsert_market_snapshot(snapshot)
            assert result is True
            latest = db.get_latest_market_snapshot()
            assert latest is not None
            assert latest.trade_date == "2024-01-15"
            assert latest.status == "completed"

    def test_upsert_updates_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, MarketSnapshot
            db = Database(db_path)
            snapshot1 = MarketSnapshot(
                trade_date="2024-01-15",
                indices_json='{"value": 100}',
                market_breadth_json='{}',
                turnover_json='{}',
                north_flow_json='{}',
                news_json='[]',
                status="pending"
            )
            db.upsert_market_snapshot(snapshot1)
            snapshot2 = MarketSnapshot(
                trade_date="2024-01-15",
                indices_json='{"value": 200}',
                market_breadth_json='{}',
                turnover_json='{}',
                north_flow_json='{}',
                news_json='[]',
                status="completed"
            )
            db.upsert_market_snapshot(snapshot2)
            latest = db.get_latest_market_snapshot()
            assert latest.status == "completed"
            with db.get_connection() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM market_snapshots"
                ).fetchone()[0]
            assert count == 1


class TestSectorRecommendation:
    def test_upsert_and_get_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, SectorRecommendation
            db = Database(db_path)
            rec = SectorRecommendation(
                trade_date="2024-01-15",
                sector_name="科技板块",
                score=85.5,
                bucket="bullish",
                reasons_json='{"reasons": ["资金流入"]}',
            )
            result = db.upsert_sector_recommendation(rec)
            assert result is True
            results = db.get_latest_sector_recommendations()
            assert len(results) > 0
            assert results[0].sector_name == "科技板块"
            assert results[0].score == 85.5

    def test_multiple_sectors_same_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, SectorRecommendation
            db = Database(db_path)
            sectors = [
                SectorRecommendation("2024-01-15", "科技板块", 85.5, "bullish", '{"r1": "a"}'),
                SectorRecommendation("2024-01-15", "银行板块", 70.0, "neutral", '{"r2": "b"}'),
                SectorRecommendation("2024-01-15", "医药板块", 60.0, "bearish", '{"r3": "c"}'),
            ]
            for s in sectors:
                db.upsert_sector_recommendation(s)
            results = db.get_latest_sector_recommendations()
            assert len(results) == 3
            assert results[0].score == 85.5
            assert results[1].score == 70.0
            assert results[2].score == 60.0


class TestStockSignal:
    def test_upsert_and_get_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, StockSignal
            db = Database(db_path)
            signal = StockSignal(
                trade_date="2024-01-15",
                stock_code="600000",
                stock_name="浦发银行",
                sector_name="银行板块",
                signal="buy",
                confidence=0.75,
                factors_json='{"factors": [{"name": "RSI", "value": 30}]}',
            )
            result = db.upsert_stock_signal(signal)
            assert result is True
            results = db.get_latest_stock_signals()
            assert len(results) > 0
            assert results[0].stock_code == "600000"
            assert results[0].signal == "buy"

    def test_get_latest_with_signal_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, StockSignal
            db = Database(db_path)
            signals = [
                StockSignal("2024-01-15", "600000", "股票A", "板块A", "buy", 0.8, '{}'),
                StockSignal("2024-01-15", "600001", "股票B", "板块B", "sell", 0.7, '{}'),
                StockSignal("2024-01-15", "600002", "股票C", "板块C", "buy", 0.6, '{}'),
            ]
            for s in signals:
                db.upsert_stock_signal(s)
            buy_signals = db.get_latest_stock_signals(signal="buy")
            assert len(buy_signals) == 2
            assert all(s.signal == "buy" for s in buy_signals)

    def test_upsert_updates_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, StockSignal
            db = Database(db_path)
            signal1 = StockSignal(
                trade_date="2024-01-15",
                stock_code="600000",
                stock_name="股票A",
                sector_name="板块A",
                signal="hold",
                confidence=0.5,
                factors_json='{}'
            )
            db.upsert_stock_signal(signal1)
            signal2 = StockSignal(
                trade_date="2024-01-15",
                stock_code="600000",
                stock_name="股票A",
                sector_name="板块A",
                signal="buy",
                confidence=0.9,
                factors_json='{}'
            )
            db.upsert_stock_signal(signal2)
            results = db.get_latest_stock_signals()
            assert len(results) == 1
            assert results[0].signal == "buy"
            assert results[0].confidence == 0.9


class TestSectorStockRecommendation:
    def test_upsert_and_get_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, SectorStockRecommendation
            db = Database(db_path)

            rec = SectorStockRecommendation(
                trade_date="2024-01-15",
                sector_name="电池",
                stock_code="300750",
                stock_name="宁德时代",
                score=3.2,
                rank_no=1,
                price=180.5,
                change_pct=2.1,
                reason="板块内领涨2.1%",
                source="sector_candidate",
                run_id="run_a",
                strategy_version="v1",
            )
            ok = db.upsert_sector_stock_recommendation(rec)
            assert ok is True

            rows = db.get_latest_sector_stock_recommendations()
            assert len(rows) == 1
            assert rows[0].stock_code == "300750"
            assert rows[0].sector_name == "电池"
            assert rows[0].rank_no == 1

    def test_batch_upsert_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, SectorStockRecommendation
            db = Database(db_path)

            recs = [
                SectorStockRecommendation(
                    trade_date="2024-01-15",
                    sector_name="电池",
                    stock_code="300750",
                    stock_name="宁德时代",
                    score=3.2,
                    rank_no=1,
                    source="sector_candidate",
                ),
                SectorStockRecommendation(
                    trade_date="2024-01-15",
                    sector_name="电池",
                    stock_code="300274",
                    stock_name="阳光电源",
                    score=2.6,
                    rank_no=2,
                    source="sector_candidate",
                ),
            ]
            assert db.batch_upsert_sector_stock_recommendations(recs) is True
            # 同批次重复写入，记录数不应增加
            assert db.batch_upsert_sector_stock_recommendations(recs) is True

            rows = db.get_sector_stock_recommendations("2024-01-15", sector_name="电池")
            assert len(rows) == 2
            assert rows[0].stock_code == "300750"
            assert rows[1].stock_code == "300274"


class TestRecommendationEvaluation:
    def test_upsert_and_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, RecommendationEvaluation
            db = Database(db_path)

            row = RecommendationEvaluation(
                recommendation_date="2024-01-15",
                recommendation_type="stock_signal",
                source="signal",
                stock_code="600519",
                stock_name="贵州茅台",
                sector_name="白酒",
                return_1d=1.2,
                return_3d=2.5,
                return_5d=3.1,
                excess_return_1d=0.4,
                excess_return_3d=0.8,
                excess_return_5d=1.1,
                is_positive_1d=1,
                is_positive_3d=1,
                is_positive_5d=1,
                evaluated_at="2024-01-20 10:00:00",
            )
            assert db.upsert_recommendation_evaluation(row) is True

            rows = db.get_recommendation_evaluations(
                recommendation_date="2024-01-15",
                recommendation_type="stock_signal",
            )
            assert len(rows) == 1
            assert rows[0].stock_code == "600519"
            assert rows[0].return_5d == 3.1

    def test_range_query_filters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, RecommendationEvaluation
            db = Database(db_path)

            rows = [
                RecommendationEvaluation(
                    recommendation_date="2024-01-15",
                    recommendation_type="stock_signal",
                    source="signal",
                    stock_code="600519",
                    stock_name="贵州茅台",
                    sector_name="白酒",
                ),
                RecommendationEvaluation(
                    recommendation_date="2024-01-16",
                    recommendation_type="sector_candidate",
                    source="sector_candidate",
                    stock_code="300750",
                    stock_name="宁德时代",
                    sector_name="电池",
                ),
            ]
            assert db.batch_upsert_recommendation_evaluations(rows) is True
            queried = db.get_recommendation_evaluations_range(
                "2024-01-16",
                "2024-01-20",
                recommendation_type="sector_candidate",
            )
            assert len(queried) == 1
            assert queried[0].stock_code == "300750"


class TestBackwardCompatibility:
    def test_followed_stocks_still_work(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            os.environ["DB_PATH"] = db_path
            if 'backend.data.db' in sys.modules:
                del sys.modules['backend.data.db']
            if 'backend.config' in sys.modules:
                del sys.modules['backend.config']
            from backend.data.db import Database, FollowedStock
            db = Database(db_path)
            stock = FollowedStock(
                stock_code="600519",
                stock_name="贵州茅台",
                cost_price=1800.0,
                volume=100
            )
            result = db.add_stock(stock)
            assert result is True
            all_stocks = db.get_all_stocks()
            assert len(all_stocks) == 1
            assert all_stocks[0].stock_code == "600519"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
