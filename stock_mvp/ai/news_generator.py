"""
AI News Generator - 生成结构化财经新闻摘要
"""
import json
from typing import List, Dict

from openai import OpenAI

from stock_mvp.config import config
from stock_mvp.db import AINews, db


class AINewsGenerator:
    """AI财经新闻生成器 - 将原始新闻转换为结构化摘要"""

    def __init__(self):
        """初始化OpenAI客户端"""
        self.client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )
        self.model = config.LLM_MODEL

    def generate_structured_news(self, raw_news: List[Dict]) -> List[Dict]:
        """
        核心方法：生成结构化新闻

        Args:
            raw_news: 原始新闻列表

        Returns:
            结构化新闻列表
        """
        if not raw_news:
            return []

        prompt = self._build_prompt(raw_news)
        result = self._call_llm(prompt)

        try:
            # 处理 Markdown 代码块
            if result:
                # 移除 ```json 和 ``` 标记
                result = result.strip()
                if result.startswith('```json'):
                    result = result[7:]
                elif result.startswith('```'):
                    result = result[3:]
                if result.endswith('```'):
                    result = result[:-3]
                result = result.strip()
            
            structured_news = json.loads(result)
            return structured_news if isinstance(structured_news, list) else []
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[AI News Generator] JSON解析失败: {e}")
            return []

    def _build_prompt(self, raw_news: List[Dict]) -> str:
        """
        构建提示词

        Args:
            raw_news: 原始新闻列表

        Returns:
            提示词字符串
        """
        news_text = "\n".join([
            f"{i+1}. [标题] {news.get('title', '')} [来源] {news.get('source', '')} [链接] {news.get('url', '')} [内容] {news.get('content', news.get('summary', ''))}"
            for i, news in enumerate(raw_news)
        ])

        prompt = f"""你是一位专业的财经新闻分析师。请根据以下原始新闻信息，生成结构化的新闻摘要。

【原始新闻】
{news_text}

请以JSON数组格式输出：
[
    {{
        "title": "新闻标题（精简概括）",
        "summary": "50-100字的新闻简介，包含具体数据和影响分析",
        "category": "宏观/行业/公司/政策/国际/科技",
        "sentiment": "positive/negative/neutral",
        "keywords": ["关键词1", "关键词2", "关键词3"],
        "importance": 8,
        "related_sectors": ["板块1", "板块2"],
        "source_url": "原始新闻链接（从原文中保留）",
        "source": "新闻来源名称"
    }}
]

要求：
1. 每条新闻简介必须包含具体数据和影响分析
2. 关键词提取要精准，适合做词云展示，每个关键词2-4个字
3. 板块关联要准确
4. source_url必须从原始新闻中保留，不要编造链接
5. importance取值1-10，数值越大越重要"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM

        Args:
            prompt: 提示词

        Returns:
            LLM返回的JSON字符串
        """
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
            
            # 处理不同的返回格式
            if hasattr(response, 'choices'):
                return response.choices[0].message.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            print(f"[AI News Generator] LLM调用失败: {e}")
            raise

    def save_to_db(self, trade_date: str, structured_news: List[Dict]) -> bool:
        """
        保存到数据库

        Args:
            trade_date: 交易日期
            structured_news: 结构化新闻列表

        Returns:
            是否保存成功
        """
        try:
            for news in structured_news:
                ai_news = AINews(
                    trade_date=trade_date,
                    title=news.get("title", ""),
                    summary=news.get("summary", ""),
                    category=news.get("category", ""),
                    sentiment=news.get("sentiment", "neutral"),
                    keywords_json=json.dumps(news.get("keywords", []), ensure_ascii=False),
                    importance=news.get("importance", 5),
                    related_sectors_json=json.dumps(news.get("related_sectors", []), ensure_ascii=False),
                    source_url=news.get("source_url", ""),
                )
                db.upsert_ai_news(ai_news)

            return True
        except Exception as e:
            print(f"保存新闻失败: {e}")
            return False


# 模块级实例
ai_news_generator = AINewsGenerator()
