"""
Tests for news_collector module — multi-source news aggregator.

Tests cover:
  - Title normalization
  - Deduplication logic (exact + fuzzy)
  - DuckDuckGo source (mocked)
  - Eastmoney source (mocked)
  - Sina source (mocked)
  - collect_all_news integration (mocked network)
  - market_data.get_news fallback behavior
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helper: uniform news item
# ---------------------------------------------------------------------------
def _make_news(title="Test", content="Body", time="2026-02-23 10:00:00",
               source="test", url="https://example.com"):
    return {"title": title, "content": content, "time": time,
            "source": source, "url": url}


# ===========================================================================
# 1. _normalize_title
# ===========================================================================
class TestNormalizeTitle:
    def test_strips_punctuation_and_spaces(self):
        from backend.data.news_collector import _normalize_title
        assert _normalize_title("A股 大涨！！") == "A股大涨"

    def test_strips_chinese_punctuation(self):
        from backend.data.news_collector import _normalize_title
        assert _normalize_title("你好，世界。") == "你好世界"

    def test_empty_string(self):
        from backend.data.news_collector import _normalize_title
        assert _normalize_title("") == ""

    def test_already_clean(self):
        from backend.data.news_collector import _normalize_title
        assert _normalize_title("科技板块领涨") == "科技板块领涨"


# ===========================================================================
# 2. _deduplicate
# ===========================================================================
class TestDeduplicate:
    def test_removes_exact_duplicate_titles(self):
        from backend.data.news_collector import _deduplicate
        items = [
            _make_news("A股大涨", content="short"),
            _make_news("A股大涨", content="longer content here"),
        ]
        result = _deduplicate(items)
        assert len(result) == 1
        # keeps longer content
        assert result[0]["content"] == "longer content here"

    def test_removes_fuzzy_duplicate(self):
        from backend.data.news_collector import _deduplicate
        items = [
            _make_news("科技板块今日大幅上涨超过5%", content="a"),
            _make_news("科技板块今日大幅上涨超5%", content="ab"),
        ]
        result = _deduplicate(items)
        assert len(result) == 1

    def test_keeps_distinct_titles(self):
        from backend.data.news_collector import _deduplicate
        items = [
            _make_news("A股收盘大涨"),
            _make_news("比特币跌破6万"),
        ]
        result = _deduplicate(items)
        assert len(result) == 2

    def test_skips_empty_titles(self):
        from backend.data.news_collector import _deduplicate
        items = [
            _make_news(""),
            _make_news("Valid Title"),
        ]
        result = _deduplicate(items)
        assert len(result) == 1
        assert result[0]["title"] == "Valid Title"

    def test_exact_dup_prefers_longer_content(self):
        from backend.data.news_collector import _deduplicate
        items = [
            _make_news("Same Title", content="x" * 100),
            _make_news("Same Title", content="y" * 10),
        ]
        result = _deduplicate(items)
        assert len(result) == 1
        assert len(result[0]["content"]) == 100


# ===========================================================================
# 3. DuckDuckGo source
# ===========================================================================
class TestFetchDuckDuckGo:
    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.DDGS")
    def test_returns_formatted_news(self, MockDDGS):
        from backend.data.news_collector import _fetch_duckduckgo
        mock_instance = MockDDGS.return_value
        mock_instance.news.return_value = [
            {
                "title": "A股大涨",
                "body": "市场全面上涨",
                "date": "2026-02-23",
                "source": "新浪财经",
                "url": "https://finance.sina.com.cn/123",
            }
        ]
        result = _fetch_duckduckgo(max_results=5)
        assert len(result) >= 1
        item = result[0]
        assert item["title"] == "A股大涨"
        assert item["content"] == "市场全面上涨"
        assert item["source"] == "新浪财经"
        assert item["url"] == "https://finance.sina.com.cn/123"

    @patch("backend.data.news_collector.HAS_DDGS", False)
    def test_returns_empty_when_ddgs_not_installed(self):
        from backend.data.news_collector import _fetch_duckduckgo
        result = _fetch_duckduckgo()
        assert result == []

    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.DDGS")
    def test_handles_exception_gracefully(self, MockDDGS):
        from backend.data.news_collector import _fetch_duckduckgo
        MockDDGS.side_effect = Exception("connection error")
        result = _fetch_duckduckgo()
        assert result == []


# ===========================================================================
# 4. Eastmoney source
# ===========================================================================
class TestFetchEastmoney:
    @patch("backend.data.news_collector.requests.get")
    def test_parses_json_response(self, mock_get):
        from backend.data.news_collector import _fetch_eastmoney
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = json.dumps({
            "data": {
                "list": [
                    {
                        "title": "东财头条",
                        "digest": "这是<b>摘要</b>内容",
                        "showTime": "2026-02-23 09:00:00",
                        "url": "https://eastmoney.com/article/1",
                    }
                ]
            }
        })
        mock_get.return_value = mock_resp

        result = _fetch_eastmoney(limit=5)
        assert len(result) >= 1
        item = result[0]
        assert item["title"] == "东财头条"
        # HTML tags should be stripped
        assert "<b>" not in item["content"]
        assert "摘要" in item["content"]
        assert item["source"] == "东方财富"

    @patch("backend.data.news_collector.requests.get")
    def test_returns_empty_on_network_error(self, mock_get):
        from backend.data.news_collector import _fetch_eastmoney
        mock_get.side_effect = Exception("timeout")
        result = _fetch_eastmoney()
        assert result == []

    @patch("backend.data.news_collector.requests.get")
    def test_strips_html_tags(self, mock_get):
        from backend.data.news_collector import _fetch_eastmoney
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = json.dumps({
            "data": {
                "list": [
                    {
                        "title": "Test",
                        "digest": "<p>Hello <strong>World</strong></p>",
                        "showTime": "2026-02-23",
                        "url": "",
                    }
                ]
            }
        })
        mock_get.return_value = mock_resp

        result = _fetch_eastmoney(limit=5)
        assert result[0]["content"] == "Hello World"


# ===========================================================================
# 5. Sina source
# ===========================================================================
class TestFetchSina:
    @patch("backend.data.news_collector.requests.get")
    def test_parses_roll_api_response(self, mock_get):
        from backend.data.news_collector import _fetch_sina
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {
                        "title": "新浪头条",
                        "intro": "这是简介",
                        "ctime": "1740268800",  # 2025-02-23 08:00:00 UTC+8
                        "url": "https://finance.sina.com.cn/art/1",
                    }
                ]
            }
        }
        mock_get.return_value = mock_resp

        result = _fetch_sina(limit=5)
        assert len(result) >= 1
        item = result[0]
        assert item["title"] == "新浪头条"
        assert item["content"] == "这是简介"
        assert item["source"] == "新浪财经"
        # Time should be converted from unix timestamp
        assert "2025" in item["time"] or "2026" in item["time"]

    @patch("backend.data.news_collector.requests.get")
    def test_converts_unix_timestamp(self, mock_get):
        from backend.data.news_collector import _fetch_sina
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "data": [
                    {
                        "title": "时间测试",
                        "intro": "content",
                        "ctime": "1740268800",
                        "url": "",
                    }
                ]
            }
        }
        mock_get.return_value = mock_resp

        result = _fetch_sina(limit=5)
        # Should be a formatted datetime string, not raw unix
        assert not result[0]["time"].isdigit()

    @patch("backend.data.news_collector.requests.get")
    def test_returns_empty_on_network_error(self, mock_get):
        from backend.data.news_collector import _fetch_sina
        mock_get.side_effect = Exception("timeout")
        result = _fetch_sina()
        assert result == []


# ===========================================================================
# 5b. Yicai source
# ===========================================================================
class TestFetchYicai:
    @patch("backend.data.news_collector.requests.get")
    def test_parses_json_response(self, mock_get):
        from backend.data.news_collector import _fetch_yicai
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            {
                "NewsTitle": "一财头条",
                "NewsNotes": "这是摘要",
                "CreateDate": "2026-02-23 10:00:00",
                "url": "/news/123",
            }
        ]
        mock_get.return_value = mock_resp
        result = _fetch_yicai(limit=5)
        assert len(result) >= 1
        assert result[0]["title"] == "一财头条"
        assert result[0]["source"] == "第一财经"
        assert "yicai.com" in result[0]["url"]

    @patch("backend.data.news_collector.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        from backend.data.news_collector import _fetch_yicai
        mock_get.side_effect = Exception("timeout")
        assert _fetch_yicai() == []


# ===========================================================================
# 5c. ThePaper source
# ===========================================================================
class TestFetchThePaper:
    @patch("backend.data.news_collector.requests.get")
    def test_parses_hot_news(self, mock_get):
        from backend.data.news_collector import _fetch_thepaper
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "hotNews": [
                    {"name": "澎湃头条", "summary": "摘要内容", "pubTimeLong": 1740268800000, "contId": "12345"}
                ],
                "financialInformationNews": [],
            }
        }
        mock_get.return_value = mock_resp
        result = _fetch_thepaper(limit=5)
        assert len(result) >= 1
        assert result[0]["title"] == "澎湃头条"
        assert result[0]["source"] == "澎湃新闻"
        assert "12345" in result[0]["url"]

    @patch("backend.data.news_collector.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        from backend.data.news_collector import _fetch_thepaper
        mock_get.side_effect = Exception("timeout")
        assert _fetch_thepaper() == []


# ===========================================================================
# 5d. Jiemian source
# ===========================================================================
class TestFetchJiemian:
    @patch("backend.data.news_collector.HAS_BS4", False)
    def test_returns_empty_without_bs4(self):
        from backend.data.news_collector import _fetch_jiemian
        assert _fetch_jiemian() == []

    @patch("backend.data.news_collector.HAS_BS4", True)
    @patch("backend.data.news_collector.requests.get")
    @patch("backend.data.news_collector.BeautifulSoup")
    def test_parses_html_fragment(self, MockBS, mock_get, ):
        from backend.data.news_collector import _fetch_jiemian
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = json.dumps({"data": '<a href="/article/123">界面头条新闻标题</a>'})
        mock_get.return_value = mock_resp

        mock_a = MagicMock()
        mock_a.get_text.return_value = "界面头条新闻标题"
        mock_a.__getitem__ = lambda self, k: "/article/123"
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [mock_a]
        MockBS.return_value = mock_soup

        result = _fetch_jiemian(limit=5)
        assert len(result) >= 1
        assert result[0]["title"] == "界面头条新闻标题"
        assert result[0]["source"] == "界面新闻"

    @patch("backend.data.news_collector.HAS_BS4", True)
    @patch("backend.data.news_collector.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        from backend.data.news_collector import _fetch_jiemian
        mock_get.side_effect = Exception("timeout")
        assert _fetch_jiemian() == []


# ===========================================================================
# 5e. Caixin source
# ===========================================================================
class TestFetchCaixin:
    @patch("backend.data.news_collector.HAS_BS4", False)
    def test_returns_empty_without_bs4(self):
        from backend.data.news_collector import _fetch_caixin
        assert _fetch_caixin() == []

    @patch("backend.data.news_collector.HAS_BS4", True)
    @patch("backend.data.news_collector.requests.get")
    @patch("backend.data.news_collector.BeautifulSoup")
    def test_parses_homepage_html(self, MockBS, mock_get):
        from backend.data.news_collector import _fetch_caixin
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "<html></html>"
        mock_get.return_value = mock_resp

        mock_a = MagicMock()
        mock_a.get_text.return_value = "财新独家：重要财经新闻标题"
        mock_a.__getitem__ = lambda self, k: "https://economy.caixin.com/2026-02-23/123.html"
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [mock_a]
        MockBS.return_value = mock_soup

        result = _fetch_caixin(limit=5)
        assert len(result) >= 1
        assert result[0]["source"] == "财新"

    @patch("backend.data.news_collector.HAS_BS4", True)
    @patch("backend.data.news_collector.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        from backend.data.news_collector import _fetch_caixin
        mock_get.side_effect = Exception("timeout")
        assert _fetch_caixin() == []


# ===========================================================================
# 5f. Guancha source
# ===========================================================================
class TestFetchGuancha:
    @patch("backend.data.news_collector.HAS_BS4", False)
    def test_returns_empty_without_bs4(self):
        from backend.data.news_collector import _fetch_guancha
        assert _fetch_guancha() == []

    @patch("backend.data.news_collector.HAS_BS4", True)
    @patch("backend.data.news_collector.requests.get")
    @patch("backend.data.news_collector.BeautifulSoup")
    def test_parses_economy_page(self, MockBS, mock_get):
        from backend.data.news_collector import _fetch_guancha
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "<html></html>"
        mock_get.return_value = mock_resp

        mock_a = MagicMock()
        mock_a.get_text.return_value = "观察者网经济频道重要新闻"
        mock_a.__getitem__ = lambda self, k: "https://www.guancha.cn/economy/2026_02_23/123.shtml"
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [mock_a]
        MockBS.return_value = mock_soup

        result = _fetch_guancha(limit=5)
        assert len(result) >= 1
        assert result[0]["source"] == "观察者网"
        assert result[0]["time"] == "2026-02-23"

    @patch("backend.data.news_collector.HAS_BS4", True)
    @patch("backend.data.news_collector.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        from backend.data.news_collector import _fetch_guancha
        mock_get.side_effect = Exception("timeout")
        assert _fetch_guancha() == []


# ===========================================================================
# 6. collect_all_news — integration
# ===========================================================================
class TestCollectAllNews:
    _PATCHES = [
        "backend.data.news_collector._fetch_guancha",
        "backend.data.news_collector._fetch_caixin",
        "backend.data.news_collector._fetch_jiemian",
        "backend.data.news_collector._fetch_thepaper",
        "backend.data.news_collector._fetch_yicai",
        "backend.data.news_collector._fetch_via_agent",
        "backend.data.news_collector._fetch_sina",
        "backend.data.news_collector._fetch_eastmoney",
        "backend.data.news_collector._fetch_duckduckgo",
    ]

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_merges_all_sources(self, mock_ddg, mock_em, mock_sina, mock_agent,
                                mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        from backend.data.news_collector import collect_all_news
        mock_ddg.return_value = [_make_news("DDG新闻", source="DuckDuckGo")]
        mock_em.return_value = [_make_news("东财新闻", source="东方财富")]
        mock_sina.return_value = [_make_news("新浪新闻", source="新浪财经")]
        mock_agent.return_value = [_make_news("Agent新闻", source="AI Agent")]
        mock_yicai.return_value = [_make_news("一财新闻", source="第一财经")]
        mock_thepaper.return_value = [_make_news("澎湃头条", source="澎湃新闻")]
        mock_jiemian.return_value = [_make_news("界面头条", source="界面新闻")]
        mock_caixin.return_value = [_make_news("财新头条", source="财新")]
        mock_guancha.return_value = [_make_news("观察头条", source="观察者网")]

        result = collect_all_news(limit=20)
        assert len(result) == 9
        sources = {item["source"] for item in result}
        for s in ("DuckDuckGo", "东方财富", "新浪财经", "AI Agent",
                   "第一财经", "澎湃新闻", "界面新闻", "财新", "观察者网"):
            assert s in sources

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_treats_empty_enabled_sources_as_all(self, mock_ddg, mock_em, mock_sina, mock_agent,
                                                  mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        from backend.data.news_collector import collect_all_news
        mock_ddg.return_value = [_make_news("DDG新闻", source="DuckDuckGo")]
        mock_em.return_value = [_make_news("东财新闻", source="东方财富")]
        mock_sina.return_value = [_make_news("新浪新闻", source="新浪财经")]
        mock_agent.return_value = []
        mock_yicai.return_value = []
        mock_thepaper.return_value = []
        mock_jiemian.return_value = []
        mock_caixin.return_value = []
        mock_guancha.return_value = []

        result = collect_all_news(limit=20, enabled_sources=[])
        assert len(result) == 3
        sources = {item["source"] for item in result}
        assert {"DuckDuckGo", "东方财富", "新浪财经"} == sources

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_deduplicates_across_sources(self, mock_ddg, mock_em, mock_sina, mock_agent,
                                         mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        from backend.data.news_collector import collect_all_news
        mock_ddg.return_value = [_make_news("A股大涨突破3000点", content="short")]
        mock_em.return_value = [_make_news("A股大涨突破3000点", content="longer content version")]
        mock_sina.return_value = []
        mock_agent.return_value = []
        mock_yicai.return_value = []
        mock_thepaper.return_value = []
        mock_jiemian.return_value = []
        mock_caixin.return_value = []
        mock_guancha.return_value = []

        result = collect_all_news(limit=20)
        assert len(result) == 1
        assert result[0]["content"] == "longer content version"

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_respects_limit(self, mock_ddg, mock_em, mock_sina, mock_agent,
                            mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        from backend.data.news_collector import collect_all_news
        mock_ddg.return_value = [_make_news(f"DDG{i}") for i in range(10)]
        mock_em.return_value = [_make_news(f"EM{i}") for i in range(10)]
        mock_sina.return_value = [_make_news(f"SINA{i}") for i in range(10)]
        mock_agent.return_value = []
        mock_yicai.return_value = []
        mock_thepaper.return_value = []
        mock_jiemian.return_value = []
        mock_caixin.return_value = []
        mock_guancha.return_value = []

        result = collect_all_news(limit=5)
        assert len(result) == 5

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_sorts_by_time_descending(self, mock_ddg, mock_em, mock_sina, mock_agent,
                                      mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        from backend.data.news_collector import collect_all_news
        mock_ddg.return_value = [_make_news("Early", time="2026-02-23 08:00:00")]
        mock_em.return_value = [_make_news("Late", time="2026-02-23 12:00:00")]
        mock_sina.return_value = [_make_news("Mid", time="2026-02-23 10:00:00")]
        mock_agent.return_value = []
        mock_yicai.return_value = []
        mock_thepaper.return_value = []
        mock_jiemian.return_value = []
        mock_caixin.return_value = []
        mock_guancha.return_value = []

        result = collect_all_news(limit=20)
        assert result[0]["title"] == "Late"
        assert result[1]["title"] == "Mid"
        assert result[2]["title"] == "Early"

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_continues_when_one_source_fails(self, mock_ddg, mock_em, mock_sina, mock_agent,
                                             mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        from backend.data.news_collector import collect_all_news
        mock_ddg.side_effect = Exception("DDG down")
        mock_em.return_value = [_make_news("东财新闻")]
        mock_sina.return_value = [_make_news("新浪新闻")]
        mock_agent.return_value = []
        mock_yicai.return_value = []
        mock_thepaper.return_value = []
        mock_jiemian.return_value = []
        mock_caixin.return_value = []
        mock_guancha.return_value = []

        result = collect_all_news(limit=20)
        assert len(result) == 2

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_returns_empty_when_all_sources_fail(self, mock_ddg, mock_em, mock_sina, mock_agent,
                                                 mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        from backend.data.news_collector import collect_all_news
        for m in (mock_ddg, mock_em, mock_sina, mock_agent,
                  mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
            m.side_effect = Exception("fail")

        result = collect_all_news(limit=20)
        assert result == []

    @patch(_PATCHES[0])
    @patch(_PATCHES[1])
    @patch(_PATCHES[2])
    @patch(_PATCHES[3])
    @patch(_PATCHES[4])
    @patch(_PATCHES[5])
    @patch(_PATCHES[6])
    @patch(_PATCHES[7])
    @patch(_PATCHES[8])
    def test_output_format(self, mock_ddg, mock_em, mock_sina, mock_agent,
                           mock_yicai, mock_thepaper, mock_jiemian, mock_caixin, mock_guancha):
        """Each news item must have title, content, time, source, url keys."""
        from backend.data.news_collector import collect_all_news
        mock_ddg.return_value = [_make_news("Test")]
        for m in (mock_em, mock_sina, mock_agent, mock_yicai, mock_thepaper,
                  mock_jiemian, mock_caixin, mock_guancha):
            m.return_value = []

        result = collect_all_news(limit=20)
        assert len(result) == 1
        for key in ("title", "content", "time", "source", "url"):
            assert key in result[0], f"Missing key: {key}"


# ===========================================================================
# 7. _execute_web_search
# ===========================================================================
class TestExecuteWebSearch:
    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.DDGS")
    def test_returns_json_string(self, MockDDGS):
        from backend.data.news_collector import _execute_web_search
        mock_instance = MockDDGS.return_value
        mock_instance.news.return_value = [
            {"title": "新闻1", "body": "内容1", "date": "2026-02-23", "source": "src", "url": "http://a.com"}
        ]
        result = _execute_web_search("A股", max_results=5)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "新闻1"

    @patch("backend.data.news_collector.HAS_DDGS", False)
    def test_returns_error_when_no_ddgs(self):
        from backend.data.news_collector import _execute_web_search
        result = _execute_web_search("A股")
        parsed = json.loads(result)
        assert "error" in parsed

    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.DDGS")
    def test_returns_error_on_exception(self, MockDDGS):
        from backend.data.news_collector import _execute_web_search
        MockDDGS.return_value.news.side_effect = Exception("search failed")
        result = _execute_web_search("A股")
        parsed = json.loads(result)
        assert "error" in parsed


# ===========================================================================
# 8. _parse_agent_response
# ===========================================================================
class TestParseAgentResponse:
    def test_parses_plain_json_array(self):
        from backend.data.news_collector import _parse_agent_response
        text = json.dumps([
            {"title": "新闻A", "content": "内容A", "time": "2026-02-23", "source": "AI", "url": "http://a.com"},
            {"title": "新闻B", "content": "内容B", "time": "2026-02-23", "source": "AI", "url": "http://b.com"},
        ])
        result = _parse_agent_response(text)
        assert len(result) == 2
        assert result[0]["title"] == "新闻A"

    def test_parses_markdown_wrapped_json(self):
        from backend.data.news_collector import _parse_agent_response
        text = '```json\n[{"title": "新闻C", "content": "c", "time": "", "source": "AI", "url": ""}]\n```'
        result = _parse_agent_response(text)
        assert len(result) == 1
        assert result[0]["title"] == "新闻C"

    def test_extracts_json_from_mixed_text(self):
        from backend.data.news_collector import _parse_agent_response
        text = '以下是搜索结果:\n[{"title": "新闻D", "content": "d", "time": "", "source": "AI", "url": ""}]\n以上是结果。'
        result = _parse_agent_response(text)
        assert len(result) == 1
        assert result[0]["title"] == "新闻D"

    def test_returns_empty_on_invalid_json(self):
        from backend.data.news_collector import _parse_agent_response
        result = _parse_agent_response("这不是JSON")
        assert result == []

    def test_returns_empty_on_empty_string(self):
        from backend.data.news_collector import _parse_agent_response
        result = _parse_agent_response("")
        assert result == []

    def test_skips_items_without_title(self):
        from backend.data.news_collector import _parse_agent_response
        text = json.dumps([
            {"title": "有标题", "content": "c", "time": "", "source": "", "url": ""},
            {"title": "", "content": "无标题", "time": "", "source": "", "url": ""},
            {"content": "也无标题", "time": "", "source": "", "url": ""},
        ])
        result = _parse_agent_response(text)
        assert len(result) == 1
        assert result[0]["title"] == "有标题"


# ===========================================================================
# 9. _fetch_via_agent
# ===========================================================================
class TestFetchViaAgent:
    @patch("backend.data.news_collector.config")
    def test_returns_empty_when_no_api_key(self, mock_config):
        from backend.data.news_collector import _fetch_via_agent
        mock_config.LLM_API_KEY = ""
        mock_config.LLM_BASE_URL = "https://api.example.com"
        mock_config.LLM_MODEL = "gpt-4o"
        result = _fetch_via_agent()
        assert result == []

    @patch("backend.data.news_collector.config")
    @patch("backend.data.news_collector.HAS_DDGS", False)
    def test_returns_empty_when_no_ddgs(self, mock_config):
        from backend.data.news_collector import _fetch_via_agent
        mock_config.LLM_API_KEY = "sk-test"
        mock_config.LLM_BASE_URL = "https://api.example.com"
        mock_config.LLM_MODEL = "gpt-4o"
        result = _fetch_via_agent()
        assert result == []

    @patch("backend.data.news_collector.config")
    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.OpenAI")
    def test_single_tool_call_then_final(self, MockOpenAI, mock_config):
        """Agent makes one tool call, then returns final text."""
        from backend.data.news_collector import _fetch_via_agent
        mock_config.LLM_API_KEY = "sk-test"
        mock_config.LLM_BASE_URL = "https://api.example.com"
        mock_config.LLM_MODEL = "gpt-4o"

        client = MockOpenAI.return_value

        # First response: tool call
        tool_call = MagicMock()
        tool_call.id = "call_1"
        tool_call.function.name = "web_search"
        tool_call.function.arguments = json.dumps({"query": "A股新闻", "max_results": 5})

        msg1 = MagicMock()
        msg1.tool_calls = [tool_call]
        msg1.content = None
        msg1.role = "assistant"

        resp1 = MagicMock()
        resp1.choices = [MagicMock(message=msg1)]

        # Second response: final text
        final_text = json.dumps([
            {"title": "A股大涨", "content": "今日大涨", "time": "2026-02-23", "source": "AI Agent", "url": "http://a.com"}
        ])
        msg2 = MagicMock()
        msg2.tool_calls = None
        msg2.content = final_text

        resp2 = MagicMock()
        resp2.choices = [MagicMock(message=msg2)]

        client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("backend.data.news_collector._execute_web_search", return_value='[{"title":"搜索结果"}]'):
            result = _fetch_via_agent(max_results=15)

        assert len(result) == 1
        assert result[0]["title"] == "A股大涨"

    @patch("backend.data.news_collector.config")
    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.OpenAI")
    def test_respects_max_tool_calls(self, MockOpenAI, mock_config):
        """Agent should stop after _MAX_AGENT_TOOL_CALLS rounds."""
        from backend.data.news_collector import _fetch_via_agent, _MAX_AGENT_TOOL_CALLS
        mock_config.LLM_API_KEY = "sk-test"
        mock_config.LLM_BASE_URL = "https://api.example.com"
        mock_config.LLM_MODEL = "gpt-4o"

        client = MockOpenAI.return_value

        # Always return tool calls (never finishes)
        tool_call = MagicMock()
        tool_call.id = "call_x"
        tool_call.function.name = "web_search"
        tool_call.function.arguments = json.dumps({"query": "test"})

        msg = MagicMock()
        msg.tool_calls = [tool_call]
        msg.content = None
        msg.role = "assistant"

        resp = MagicMock()
        resp.choices = [MagicMock(message=msg)]

        client.chat.completions.create.return_value = resp

        with patch("backend.data.news_collector._execute_web_search", return_value='[]'):
            result = _fetch_via_agent()

        # Should return empty (never got final text) but not loop forever
        assert isinstance(result, list)
        assert client.chat.completions.create.call_count <= _MAX_AGENT_TOOL_CALLS + 1

    @patch("backend.data.news_collector._fetch_agent_fallback")
    @patch("backend.data.news_collector.config")
    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.OpenAI")
    def test_falls_back_on_unsupported_function_calling(self, MockOpenAI, mock_config, mock_fallback):
        """If proxy returns 400/unsupported, should fall back to _fetch_agent_fallback."""
        from backend.data.news_collector import _fetch_via_agent
        mock_config.LLM_API_KEY = "sk-test"
        mock_config.LLM_BASE_URL = "https://api.example.com"
        mock_config.LLM_MODEL = "gpt-4o"

        client = MockOpenAI.return_value
        client.chat.completions.create.side_effect = Exception("400: tools is not supported")

        mock_fallback.return_value = [_make_news("Fallback新闻", source="AI Agent")]

        result = _fetch_via_agent()
        assert mock_fallback.called
        assert len(result) == 1
        assert result[0]["title"] == "Fallback新闻"

    @patch("backend.data.news_collector.config")
    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.OpenAI")
    def test_returns_empty_on_generic_exception(self, MockOpenAI, mock_config):
        """Generic exceptions (not FC-related) should return []."""
        from backend.data.news_collector import _fetch_via_agent
        mock_config.LLM_API_KEY = "sk-test"
        mock_config.LLM_BASE_URL = "https://api.example.com"
        mock_config.LLM_MODEL = "gpt-4o"

        client = MockOpenAI.return_value
        client.chat.completions.create.side_effect = Exception("network timeout")

        result = _fetch_via_agent()
        assert result == []


# ===========================================================================
# 10. _fetch_agent_fallback
# ===========================================================================
class TestFetchAgentFallback:
    @patch("backend.data.news_collector.HAS_DDGS", True)
    @patch("backend.data.news_collector.DDGS")
    def test_generates_keywords_and_merges(self, MockDDGS):
        from backend.data.news_collector import _fetch_agent_fallback

        mock_client = MagicMock()

        # Step 1: LLM generates keywords
        kw_resp = MagicMock()
        kw_msg = MagicMock()
        kw_msg.content = "A股行情\n央行政策\n半导体出口"
        kw_resp.choices = [MagicMock(message=kw_msg)]

        # Step 2: LLM merges results
        merge_text = json.dumps([
            {"title": "合并新闻", "content": "内容", "time": "2026-02-23", "source": "AI Agent", "url": ""}
        ])
        merge_resp = MagicMock()
        merge_msg = MagicMock()
        merge_msg.content = merge_text
        merge_resp.choices = [MagicMock(message=merge_msg)]

        mock_client.chat.completions.create.side_effect = [kw_resp, merge_resp]

        # DDGS mock
        MockDDGS.return_value.news.return_value = [
            {"title": "搜索结果", "body": "内容", "date": "2026-02-23", "source": "src", "url": "http://a.com"}
        ]

        result = _fetch_agent_fallback(mock_client, "2026-02-23", max_results=10)
        assert len(result) == 1
        assert result[0]["title"] == "合并新闻"

    def test_returns_empty_on_exception(self):
        from backend.data.news_collector import _fetch_agent_fallback

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("LLM error")

        result = _fetch_agent_fallback(mock_client, "2026-02-23")
        assert result == []


# ===========================================================================
# 11. market_data.get_news fallback
# ===========================================================================
class TestMarketDataGetNewsFallback:
    def test_uses_news_collector_first(self):
        """get_news should prefer news_collector over akshare."""
        from backend.data.market_data import MarketData
        m = MarketData()

        with patch("backend.data.news_collector.collect_all_news") as mock_collect, \
             patch("backend.data.market_data.ak") as mock_ak:
            mock_collect.return_value = [_make_news("From Collector")]
            result = m.get_news(limit=5)
            assert len(result) == 1
            assert result[0]["title"] == "From Collector"
            # akshare should NOT have been called
            mock_ak.stock_news_em.assert_not_called()

    def test_falls_back_to_akshare_on_collector_failure(self):
        """If news_collector fails, should fall back to akshare."""
        import pandas as pd
        from backend.data.market_data import MarketData
        m = MarketData()

        with patch("backend.data.news_collector.collect_all_news", side_effect=Exception("collector broken")), \
             patch("backend.data.market_data.ak") as mock_ak:
            mock_ak.stock_news_em.return_value = pd.DataFrame({
                '新闻标题': ['AK新闻'],
                '新闻内容': ['akshare content'],
                '发布时间': ['2026-02-23'],
                '文章来源': ['东方财富'],
                '新闻链接': ['https://ak.com/1'],
            })
            result = m.get_news(limit=5)
            assert len(result) == 1
            assert result[0]["title"] == "AK新闻"

    def test_returns_empty_when_all_fail(self):
        """If both collector and akshare fail, return []."""
        from backend.data.market_data import MarketData
        m = MarketData()

        with patch("backend.data.news_collector.collect_all_news", side_effect=Exception("broken")), \
             patch("backend.data.market_data.ak") as mock_ak:
            mock_ak.stock_news_em.side_effect = Exception("akshare broken")
            result = m.get_news(limit=5)
            assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
