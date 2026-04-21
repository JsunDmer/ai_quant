"""
配置管理模块
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# 本文件所在目录即 backend/；相对 DB_PATH 一律相对此目录解析，避免 cwd 不同生成多份 .db
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_db_path(raw: str | None) -> str:
    value = (raw or "backend.db").strip() or "backend.db"
    if os.path.isabs(value):
        return os.path.normpath(value)
    return os.path.normpath(os.path.join(_BACKEND_DIR, value))


_RESOLVED_DB_PATH = _resolve_db_path(os.getenv("DB_PATH"))


@dataclass
class Config:
    """应用配置"""
    
    # LLM 模式选择
    LLM_MODE: str = os.getenv("LLM_MODE", "openai")  # "openai" 或 "opencode"
    
    # OpenAI 兼容接口配置
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    LLM_MODEL: str = os.getenv("LLM_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    
    # OpenCode 服务器配置
    OPENCODE_SERVER_URL: str = os.getenv("OPENCODE_SERVER_URL", "http://localhost:63424")
    
    # 兼容旧配置
    DEEPSEEK_API_KEY: str = LLM_API_KEY
    DEEPSEEK_BASE_URL: str = LLM_BASE_URL
    DEEPSEEK_MODEL: str = LLM_MODEL
    
    # 钉钉推送配置
    DINGDING_WEBHOOK: str = os.getenv("DINGDING_WEBHOOK", "")
    
    # 数据库路径（相对路径相对于 backend/，与进程 cwd 无关）
    DB_PATH: str = _RESOLVED_DB_PATH
    
    # AI 分析配置
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.7
    
    # 报警配置
    DEFAULT_ALARM_PERCENT: float = 3.0

    DATA_SOURCE_PRIORITY: str = os.getenv("DATA_SOURCE_PRIORITY", "akshare,efinance,tushare")
    REALTIME_SOURCE_PRIORITY: str = os.getenv(
        "REALTIME_SOURCE_PRIORITY",
        "akshare_em,akshare_sina,akshare_tencent",
    )
    
    # 收盘模式配置
    TRADING_TIMEZONE: str = os.getenv("TRADING_TIMEZONE", "Asia/Shanghai")
    TRADING_DAY_CHECK_TIME: str = os.getenv("TRADING_DAY_CHECK_TIME", "15:30")  # 交易日检查时间
    PIPELINE_RETRY_COUNT: int = int(os.getenv("PIPELINE_RETRY_COUNT", "3"))
    PIPELINE_TIMEOUT: int = int(os.getenv("PIPELINE_TIMEOUT", "300"))  # 单步超时秒数

    def __post_init__(self) -> None:
        object.__setattr__(self, "DB_PATH", _resolve_db_path(self.DB_PATH))


# 全局配置实例
config = Config()
