from unittest.mock import MagicMock, patch

import pytest

from backend.ai.news_generator import AINewsGenerator
from backend.ai.sector_analyzer import AISectorAnalyzer
from backend.ai.opencode_client import is_opencode_mode, request_opencode
from backend.config import config


def test_is_opencode_mode_true(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "opencode")
    assert is_opencode_mode() is True


def test_is_opencode_mode_false(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "openai")
    assert is_opencode_mode() is False


def test_request_opencode_success(monkeypatch):
    monkeypatch.setattr(config, "OPENCODE_SERVER_URL", "http://localhost:63424")

    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.content = b'{"id":"sid-1"}'
    session_resp.json.return_value = {"id": "sid-1"}

    message_resp = MagicMock()
    message_resp.status_code = 200
    message_resp.content = b'{}'
    message_resp.json.return_value = {
        "parts": [
            {"type": "text", "text": "```json"},
            {"type": "text", "text": '[{"title":"ok"}]'},
            {"type": "text", "text": "```"},
        ]
    }

    with patch("backend.ai.opencode_client.requests.post", side_effect=[session_resp, message_resp]) as mock_post:
        result = request_opencode(
            "user prompt",
            title="news-analysis",
            system_prompt="system prompt",
        )

    assert result == '```json\n[{"title":"ok"}]\n```'
    assert mock_post.call_count == 2


def test_request_opencode_missing_session_id(monkeypatch):
    monkeypatch.setattr(config, "OPENCODE_SERVER_URL", "http://localhost:63424")

    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.content = b'{}'
    session_resp.json.return_value = {}

    with patch("backend.ai.opencode_client.requests.post", return_value=session_resp):
        with pytest.raises(RuntimeError, match="缺少 id"):
            request_opencode("prompt", title="news-analysis")


def test_request_opencode_non_json_response(monkeypatch):
    monkeypatch.setattr(config, "OPENCODE_SERVER_URL", "http://localhost:63424")

    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.content = b"not-json"
    session_resp.text = "not-json"
    session_resp.json.side_effect = ValueError("bad json")

    with patch("backend.ai.opencode_client.requests.post", return_value=session_resp):
        with pytest.raises(RuntimeError, match="非 JSON"):
            request_opencode("prompt", title="news-analysis")


def test_news_generator_uses_opencode_mode(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "opencode")
    generator = AINewsGenerator()
    assert generator._use_opencode is True

    with patch("backend.ai.news_generator.request_opencode", return_value="[]") as mock_call:
        result = generator.generate_structured_news([{"title": "测试"}])

    assert result == []
    assert mock_call.called


def test_sector_analyzer_uses_opencode_mode(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "opencode")
    analyzer = AISectorAnalyzer()
    assert analyzer._use_opencode is True

    with patch(
        "backend.ai.sector_analyzer.request_opencode",
        return_value='{"sector_analysis":[],"market_overview":"","hot_sectors":[]}',
    ) as mock_call:
        result = analyzer.analyze_sectors([{"title": "测试", "summary": "摘要"}], sector_names=["半导体"])

    assert isinstance(result, dict)
    assert "sector_analysis" in result
    assert mock_call.called
