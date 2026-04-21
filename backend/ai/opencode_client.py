"""
OpenCode ACP 客户端工具
"""
from __future__ import annotations

from typing import Any

import requests

from backend.config import config


def is_opencode_mode() -> bool:
    """是否启用 OpenCode 模式"""
    return (config.LLM_MODE or "").strip().lower() == "opencode"


def request_opencode(prompt: str, *, title: str, system_prompt: str = "") -> str:
    """
    通过 OpenCode ACP 服务发送消息并返回文本结果

    Args:
        prompt: 用户提示词
        title: 会话标题
        system_prompt: 系统提示词（会拼接到消息前部）

    Returns:
        OpenCode 返回的文本
    """
    base_url = (config.OPENCODE_SERVER_URL or "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("OPENCODE_SERVER_URL 未配置")

    message_text = f"{system_prompt}\n\n{prompt}".strip() if system_prompt else prompt

    session_resp = requests.post(
        f"{base_url}/session",
        json={"title": title},
        timeout=20,
    )
    if session_resp.status_code >= 400:
        raise RuntimeError(
            f"OpenCode 创建会话失败: {session_resp.status_code} {session_resp.text[:300]}"
        )

    try:
        session_payload = session_resp.json() if session_resp.content else {}
    except ValueError as exc:
        raise RuntimeError(f"OpenCode 创建会话返回非 JSON: {session_resp.text[:300]}") from exc
    session_id = session_payload.get("id")
    if not session_id:
        raise RuntimeError("OpenCode 创建会话返回缺少 id")

    message_resp = requests.post(
        f"{base_url}/session/{session_id}/message",
        json={"parts": [{"type": "text", "text": message_text}]},
        timeout=120,
    )
    if message_resp.status_code >= 400:
        raise RuntimeError(
            f"OpenCode 发送消息失败: {message_resp.status_code} {message_resp.text[:300]}"
        )

    try:
        payload = message_resp.json() if message_resp.content else {}
    except ValueError as exc:
        raise RuntimeError(f"OpenCode 消息响应非 JSON: {message_resp.text[:300]}") from exc
    text_parts = _collect_text_parts(payload)
    if text_parts:
        return "\n".join(text_parts).strip()

    raise RuntimeError(f"OpenCode 响应中未找到文本内容: {str(payload)[:300]}")


def _collect_text_parts(node: Any) -> list[str]:
    """递归提取 ACP 响应里的文本片段"""
    out: list[str] = []

    def _walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "text":
                text = value.get("text")
                if isinstance(text, str) and text.strip():
                    out.append(text)
            for child in value.values():
                _walk(child)
        elif isinstance(value, list):
            for item in value:
                _walk(item)

    _walk(node)
    return out
