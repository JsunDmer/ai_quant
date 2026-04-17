"""
AI News Generator - 生成结构化财经新闻摘要
"""
import json
import os
import asyncio
import requests
from typing import List, Dict

from config import config
from db import AINews, db

def _use_opencode_mode():
    return os.getenv("LLM_MODE", "") == "opencode"


class AINewsGenerator:
    def __init__(self):
        self._use_opencode = _use_opencode_mode()
        if not self._use_opencode:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.LLM_API_KEY,
                base_url=config.LLM_BASE_URL
            )
            self.model = config.LLM_MODEL

    def generate_structured_news(self, raw_news: List[Dict]) -> List[Dict]:
        if self._use_opencode:
            return self._generate_opencode(raw_news)
        return self._generate_openai(raw_news)

    def _generate_opencode(self, raw_news: List[Dict]) -> List[Dict]:
        try:
            prompt = self._build_prompt(raw_news)
            server_url = config.OPENCODE_SERVER_URL
            resp = requests.post(
                f"{server_url}/session",
                json={"title": "news-analysis"},
                timeout=30
            )
            if resp.status_code != 200:
                return []
            session = resp.json()
            session_id = session.get("id")
            if not session_id:
                return []
            msg_resp = requests.post(
                f"{server_url}/session/{session_id}/message",
                json={"parts": [{"type": "text", "text": prompt}]},
                timeout=60
            )
            if msg_resp.status_code != 200:
                return []
            result_data = msg_resp.json()
            result = ""
            for part in result_data.get("parts", []):
                if part.get("type") == "text":
                    result += part.get("text", "")
            return self._parse_result(result, raw_news)
        except Exception as e:
            print(f"[AINewsGenerator] OpenCode调用失败: {e}")
            return []

    def _generate_openai(self, raw_news: List[Dict]) -> List[Dict]:
        prompt = self._build_prompt(raw_news)
        result = self._call_llm(prompt)
        return self._parse_result(result, raw_news)

    def _build_prompt(self, raw_news: List[Dict]) -> str:
        news_json = json.dumps(raw_news[:10], ensure_ascii=False, indent=2)
        return f"""请分析以下财经新闻，提取关键信息并返回结构化数据。

新闻列表:
{news_json}

请返回JSON数组格式，每条新闻包含:
- title: 标题
- summary: 摘要 (50字以内)
- sentiment: 情绪 (positive/neutral/negative)
- keywords: 关键词 (最多5个)
- related_sectors: 关联板块
- importance: 重要性 (1-5)

直接返回JSON数组，不要其他说明。"""

    def _call_llm(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的财经新闻分析师，擅长提取关键信息和分析市场影响。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            if hasattr(response, 'choices'):
                return response.choices[0].message.content
            return str(response)
        except Exception as e:
            print(f"[AINewsGenerator] LLM调用失败: {e}")
            return "[]"

    def _parse_result(self, result: str, raw_news: List[Dict]) -> List[Dict]:
        try:
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            elif result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            data = json.loads(result.strip())
            if not isinstance(data, list):
                data = [data]
            return data
        except json.JSONDecodeError:
            print(f"[AINewsGenerator] JSON解析失败: {result[:100]}")
            return []

    def save_to_db(self, structured_news: List[Dict], trade_date: str):
        for item in structured_news:
            news = AINews(
                trade_date=trade_date,
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                sentiment=item.get("sentiment", "neutral"),
                keywords=",".join(item.get("keywords", [])),
                related_sectors=",".join(item.get("related_sectors", [])),
                importance=item.get("importance", 3),
            )
            db.session.add(news)
        db.session.commit()