"""
配置管理模块
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """应用配置"""
    
    # LLM API 配置 (支持 OpenAI 兼容接口)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    LLM_MODEL: str = os.getenv("LLM_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    
    # 兼容旧配置
    DEEPSEEK_API_KEY: str = LLM_API_KEY
    DEEPSEEK_BASE_URL: str = LLM_BASE_URL
    DEEPSEEK_MODEL: str = LLM_MODEL
    
    # 钉钉推送配置
    DINGDING_WEBHOOK: str = os.getenv("DINGDING_WEBHOOK", "")
    
    # 数据库路径
    DB_PATH: str = os.getenv("DB_PATH", "stock_mvp.db")
    
    # AI 分析配置
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.7
    
    # 报警配置
    DEFAULT_ALARM_PERCENT: float = 3.0
    
    # 收盘模式配置
    TRADING_TIMEZONE: str = os.getenv("TRADING_TIMEZONE", "Asia/Shanghai")
    TRADING_DAY_CHECK_TIME: str = os.getenv("TRADING_DAY_CHECK_TIME", "15:30")  # 交易日检查时间
    PIPELINE_RETRY_COUNT: int = int(os.getenv("PIPELINE_RETRY_COUNT", "3"))
    PIPELINE_TIMEOUT: int = int(os.getenv("PIPELINE_TIMEOUT", "300"))  # 单步超时秒数


# 全局配置实例
config = Config()
