"""
AI Sector Analyzer - AI板块分析服务
"""
import json
import asyncio
import requests
from typing import List, Dict, Any

import os
from config import config
from db import AISectorAnalysis, db

def _use_opencode_mode():
    return os.getenv("LLM_MODE", "") == "opencode"


class AISectorAnalyzer:
    MAIN_SECTORS = [
        "科技", "新能源", "医药", "消费", "金融", "地产",
        "军工", "芯片", "人工智能", "半导体", "光伏", "储能",
        "汽车", "白酒", "银行", "证券", "保险", "基建",
        "建材", "有色", "煤炭", "石油", "电力", "钢铁",
        "化工", "机械", "交通运输", "传媒", "电子", "计算机"
    ]

    def __init__(self):
        self._use_opencode = _use_opencode_mode()
        if not self._use_opencode:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.LLM_API_KEY,
                base_url=config.LLM_BASE_URL
            )
            self.model = config.LLM_MODEL

    def analyze_sectors(self, ai_news_list: List[Dict], sector_names: List[str] = None) -> Dict[str, Any]:
        if self._use_opencode:
            return self._analyze_opencode(ai_news_list, sector_names)
        return self._analyze_openai(ai_news_list, sector_names)

    def _analyze_opencode(self, ai_news_list: List[Dict], sector_names: List[str] = None) -> Dict[str, Any]:
        try:
            prompt = self._build_prompt(ai_news_list, sector_names)
            server_url = config.OPENCODE_SERVER_URL
            resp = requests.post(
                f"{server_url}/session",
                json={"title": "sector-analysis"},
                timeout=30
            )
            if resp.status_code != 200:
                return {"sector_analysis": [], "market_overview": "解析失败", "hot_sectors": []}
            session = resp.json()
            session_id = session.get("id")
            if not session_id:
                return {"sector_analysis": [], "market_overview": "解析失败", "hot_sectors": []}
            msg_resp = requests.post(
                f"{server_url}/session/{session_id}/message",
                json={"parts": [{"type": "text", "text": prompt}]},
                timeout=60
            )
            if msg_resp.status_code != 200:
                return {"sector_analysis": [], "market_overview": "解析失败", "hot_sectors": []}
            result_data = msg_resp.json()
            result = ""
            for part in result_data.get("parts", []):
                if part.get("type") == "text":
                    result += part.get("text", "")
            return self._parse_result(result)
        except Exception as e:
            print(f"[AISectorAnalyzer] OpenCode调用失败: {e}")
            return {"sector_analysis": [], "market_overview": "解析失败", "hot_sectors": []}

    def _analyze_openai(self, ai_news_list: List[Dict], sector_names: List[str] = None) -> Dict[str, Any]:
        prompt = self._build_prompt(ai_news_list, sector_names)
        result = self._call_llm(prompt)
        return self._parse_result(result)

    def _build_prompt(self, ai_news_list: List[Dict], sector_names: List[str] = None) -> str:
        sectors = sector_names or self.MAIN_SECTORS
        sector_list_text = ", ".join(sectors[:15])
        news_text = json.dumps(ai_news_list[:10], ensure_ascii=False)[:2000]
        return f"""你是一位专业的A股板块分析师。请基于今日新闻，分析各板块的涨跌趋势。

【今日新闻】
{news_text}

请以JSON格式输出：
{{
    "sector_analysis": [
        {{
            "sector": "板块名称",
            "direction": "up/down/neutral",
            "confidence": 8,
            "score_up": 75,
            "score_down": 25,
            "reasons": ["利好1", "利好2"],
            "related_news_indices": [0, 2]
        }}
    ],
    "market_overview": "整体市场观点，30字以内",
    "hot_sectors": ["板块1", "板块2"]
}}

要求：
1. 每个板块必须基于新闻内容给出判断
2. confidence表示判断的把握程度(1-10)
3. score_up + score_down 应接近 100
4. reasons要具体引用新闻内容
5. 只分析有新闻支撑的板块，不要凭空捏造
6. 输出必须是合法的JSON格式
7. 板块名称必须从以下列表中选择: {sector_list_text}"""

    def _call_llm(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的A股板块分析师，擅长分析板块涨跌趋势。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            if hasattr(response, 'choices'):
                return response.choices[0].message.content
            return str(response)
        except Exception as e:
            print(f"[AI Sector Analyzer] LLM调用失败: {e}")
            raise

    def _parse_result(self, result: str) -> Dict[str, Any]:
        try:
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            elif result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            return json.loads(result.strip())
        except json.JSONDecodeError:
            print(f"[AI Sector Analyzer] JSON解析失败: {result[:200]}")
            return {"sector_analysis": [], "market_overview": "解析失败", "hot_sectors": []}

    def save_to_db(self, trade_date: str, analysis: Dict[str, Any]) -> bool:
        try:
            sector_analysis = analysis.get('sector_analysis', [])
            for sector_data in sector_analysis:
                ai_sector = AISectorAnalysis(
                    trade_date=trade_date,
                    sector_name=sector_data.get('sector', ''),
                    direction=sector_data.get('direction', 'neutral'),
                    confidence=sector_data.get('confidence', 5),
                    score_up=sector_data.get('score_up', 50),
                    score_down=sector_data.get('score_down', 50),
                    reasons=";".join(sector_data.get('reasons', [])),
                    related_news_indices=",".join(map(str, sector_data.get('related_news_indices', [])))
                )
                db.session.add(ai_sector)
            db.session.commit()
            return True
        except Exception as e:
            print(f"[AI Sector Analyzer] 保存失败: {e}")
            db.session.rollback()
            return False