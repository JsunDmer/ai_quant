"""
AI Sector Analyzer - AI板块分析服务
基于AI生成的新闻，分析各板块的涨跌趋势
"""
import json
from typing import List, Dict, Any

from backend.config import config
from backend.ai.opencode_client import is_opencode_mode, request_opencode
from backend.data.db import AISectorAnalysis, db


class AISectorAnalyzer:
    """AI板块分析器 - 基于新闻分析板块涨跌"""
    
    # 主要板块列表
    MAIN_SECTORS = [
        "科技", "新能源", "医药", "消费", "金融", "地产",
        "军工", "芯片", "人工智能", "半导体", "光伏", "储能",
        "汽车", "白酒", "银行", "证券", "保险", "基建",
        "建材", "有色", "煤炭", "石油", "电力", "钢铁",
        "化工", "机械", "交通运输", "传媒", "电子", "计算机"
    ]
    
    def __init__(self):
        """按配置初始化 LLM 客户端"""
        self._use_opencode = is_opencode_mode()
        self.model = config.LLM_MODEL
        self.client = None
        if not self._use_opencode:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.LLM_API_KEY,
                base_url=config.LLM_BASE_URL
            )
    
    def analyze_sectors(self, ai_news_list: List[Dict], sector_names: List[str] = None) -> Dict[str, Any]:
        """
        基于AI新闻分析板块

        Args:
            ai_news_list: AI生成的新闻列表
            sector_names: 动态板块名列表（来自AKShare），None时使用MAIN_SECTORS

        Returns:
            {
                "sector_analysis": [...],
                "market_overview": "...",
                "hot_sectors": [...]
            }
        """
        if not ai_news_list:
            return {"sector_analysis": [], "market_overview": "", "hot_sectors": []}

        prompt = self._build_prompt(ai_news_list, sector_names=sector_names)
        result = self._call_llm(prompt)
        
        try:
            # 处理 Markdown 代码块
            if result:
                result = result.strip()
                if result.startswith('```json'):
                    result = result[7:]
                elif result.startswith('```'):
                    result = result[3:]
                if result.endswith('```'):
                    result = result[:-3]
                result = result.strip()
            
            analysis = json.loads(result)
            return analysis
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[AI Sector Analyzer] JSON解析失败: {e}")
            return {"sector_analysis": [], "market_overview": "", "hot_sectors": []}
    
    def _build_prompt(self, ai_news_list: List[Dict], sector_names: List[str] = None) -> str:
        """构建板块分析提示词"""

        # 确定板块列表
        sectors_pool = sector_names if sector_names else self.MAIN_SECTORS
        sector_list_text = "、".join(sectors_pool[:100])  # 限制长度

        # 格式化新闻列表
        news_text = ""
        for i, news in enumerate(ai_news_list):
            title = news.get('title', '')
            summary = news.get('summary', '')
            category = news.get('category', '')
            sentiment = news.get('sentiment', 'neutral')
            sectors = news.get('related_sectors_json', '[]')
            try:
                sectors = json.loads(sectors) if isinstance(sectors, str) else sectors
            except:
                sectors = []

            news_text += f"""
{i+1}. 【{title}】
   简介: {summary}
   分类: {category} | 情绪: {sentiment}
   相关板块: {', '.join(sectors) if sectors else '无'}
"""

        prompt = f"""你是一位专业的A股板块分析师。请基于今日新闻，分析各板块的涨跌趋势。

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
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        try:
            if self._use_opencode:
                return request_opencode(
                    prompt,
                    title="sector-analysis",
                    system_prompt="你是一位专业的A股板块分析师，擅长分析板块涨跌趋势。",
                )

            if self.client is None:
                raise RuntimeError("OpenAI 客户端未初始化")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的A股板块分析师，擅长分析板块涨跌趋势。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # 处理不同的返回格式
            if hasattr(response, 'choices'):
                return response.choices[0].message.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            print(f"[AI Sector Analyzer] LLM调用失败: {e}")
            raise
    
    def save_to_db(self, trade_date: str, analysis: Dict[str, Any]) -> bool:
        """保存分析结果到数据库"""
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
                    reasons_json=json.dumps(sector_data.get('reasons', []), ensure_ascii=False),
                    related_news_json=json.dumps(sector_data.get('related_news_indices', []), ensure_ascii=False)
                )
                db.upsert_ai_sector_analysis(ai_sector)
            
            return True
        except Exception as e:
            print(f"保存板块分析失败: {e}")
            return False


# 模块级实例
ai_sector_analyzer = AISectorAnalyzer()
