"""
AI Agent 分析服务 - 基于 LLM 的投资分析
"""
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI

from config import config


class AIAnalysisService:
    """AI 分析服务"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )
        self.model = config.LLM_MODEL
    
    def analyze_market(
        self, 
        news: List[Dict], 
        cn_indices: Dict, 
        us_indices: Dict
    ) -> Dict[str, Any]:
        """
        分析市场环境
        
        Args:
            news: 新闻列表 [{title, time, source, url}]
            cn_indices: A股指数 {上证, 深证, 创业板}
            us_indices: 美股指数 {道指, 纳指, 标普}
        
        Returns:
            {
                "market_view": "中性偏乐观",
                "key_insight": "...",
                "hot_keywords": ["AI", "新能源", ...]
            }
        """
        prompt = f"""
你是一位专业的A股投资顾问。请分析以下市场信息：

【A股指数】
{json.dumps(cn_indices, ensure_ascii=False, indent=2)}

【美股指数】
{json.dumps(us_indices, ensure_ascii=False, indent=2)}

【重要新闻】
{self._format_news(news[:10])}

请以JSON格式输出：
{{
    "market_view": "乐观/中性偏乐观/中性/中性偏谨慎/谨慎",
    "key_insight": "50字以内的市场核心观点",
    "hot_keywords": ["关键词1", "关键词2", "关键词3"]
}}
"""
        return self._call_llm(prompt)
    
    def analyze_sectors(
        self,
        sector_scores: List[Dict],
        market_context: Dict
    ) -> Dict[str, Any]:
        """
        分析板块，给出买入/规避建议
        
        Args:
            sector_scores: 板块评分 [{name, score, reasons}]
            market_context: 市场环境 {market_view, key_insight}
        
        Returns:
            {
                "buy_sectors": [
                    {"name": "科技", "confidence": 8, "reason": "..."}
                ],
                "avoid_sectors": [
                    {"name": "房地产", "reason": "..."}
                ]
            }
        """
        prompt = f"""
你是一位专业的A股投资顾问。请根据板块数据给出投资建议。

【市场环境】
{market_context.get('market_view', '未知')} - {market_context.get('key_insight', '')}

【板块评分数据】
{self._format_sectors(sector_scores)}

请以JSON格式输出：
{{
    "buy_sectors": [
        {{"name": "板块名", "confidence": 8, "reason": "推荐理由"}}
    ],
    "avoid_sectors": [
        {{"name": "板块名", "reason": "规避理由"}}
    ]
}}

要求：
1. buy_sectors 最多3个，confidence 为1-10整数
2. avoid_sectors 最多2个
3. 理由简洁（20字以内）
"""
        return self._call_llm(prompt)
    
    def analyze_stocks(
        self,
        signals: List[Dict],
        portfolio: List[str] = None
    ) -> Dict[str, Any]:
        """
        分析股票，给出买卖建议
        
        Args:
            signals: 信号列表 [{stock_code, stock_name, signal, confidence, factors}]
            portfolio: 用户持仓股票代码列表
        
        Returns:
            {
                "buy_stocks": [
                    {"code": "600000", "name": "浦发银行", "confidence": 8, "reason": "..."}
                ],
                "sell_stocks": [
                    {"code": "000001", "name": "平安银行", "confidence": 7, "reason": "..."}
                ]
            }
        """
        portfolio_str = f"用户持仓: {', '.join(portfolio)}" if portfolio else "用户暂无持仓"
        
        prompt = f"""
你是一位专业的A股投资顾问。请根据信号数据给出买卖建议。

【用户持仓】
{portfolio_str}

【股票信号数据】
{self._format_signals(signals[:20])}

请以JSON格式输出：
{{
    "buy_stocks": [
        {{"code": "代码", "name": "名称", "confidence": 8, "reason": "推荐理由"}}
    ],
    "sell_stocks": [
        {{"code": "代码", "name": "名称", "confidence": 7, "reason": "卖出理由"}}
    ]
}}

要求：
1. buy_stocks 最多5个，confidence 为1-10整数
2. sell_stocks 优先包含用户持仓中的股票
3. 理由简洁（20字以内）
"""
        return self._call_llm(prompt)
    
    def _format_news(self, news: List[Dict]) -> str:
        """格式化新闻"""
        lines = []
        for n in news:
            lines.append(f"- [{n.get('source', '未知')}] {n.get('title', '')}")
        return "\n".join(lines)
    
    def _format_sectors(self, sectors: List[Dict]) -> str:
        """格式化板块数据"""
        lines = []
        for s in sectors[:15]:
            reasons = s.get('reasons', [])
            reason_str = reasons[0] if reasons else ''
            lines.append(f"- {s.get('name', '未知')}: 评分{s.get('score', 0):.1f}, {reason_str}")
        return "\n".join(lines)
    
    def _format_signals(self, signals: List[Dict]) -> str:
        """格式化信号数据"""
        lines = []
        for s in signals:
            factors = s.get('factors', [])
            factor_str = factors[0] if factors else ''
            lines.append(f"- {s.get('stock_code', '')} {s.get('stock_name', '')}: "
                        f"{s.get('signal', '')}, 置信度{s.get('confidence', 0):.0%}")
        return "\n".join(lines)
    
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用 LLM 并解析 JSON 响应"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"AI 分析失败: {e}")
            return {
                "error": str(e),
                "market_view": "分析失败",
                "key_insight": "AI 分析暂时不可用",
                "buy_sectors": [],
                "avoid_sectors": [],
                "buy_stocks": [],
                "sell_stocks": []
            }


# 模块级实例
ai_analysis = AIAnalysisService()
