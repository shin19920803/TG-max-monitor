"""
TG-max-monitor 設定檔
集中管理所有常數與環境變數
"""
import os
from dataclasses import dataclass


@dataclass
class USDTConfig:
    """USDT 監控設定"""
    threshold: float = float(os.getenv("USDT_THRESHOLD", "0.2"))
    change_threshold: float = float(os.getenv("USDT_CHANGE_THRESHOLD", "0"))
    state_file: str = "last_state.txt"
    bank_spread_fix: float = float(os.getenv("BANK_SPREAD_FIX", "0.05"))


@dataclass
class BTCConfig:
    """BTC 監控設定"""
    drop_threshold: float = float(os.getenv("BTC_DROP_THRESHOLD", "0.01"))
    time_window: int = int(os.getenv("BTC_TIME_WINDOW", "3600"))
    history_file: str = "btc_history.json"


@dataclass
class TelegramConfig:
    """Telegram 設定"""
    token: str = os.getenv("TG_TOKEN", "").replace(" ", "").replace("\n", "").strip()
    chat_id: str = os.getenv("TG_CHAT_ID", "").replace(" ", "").replace("\n", "").strip()
    api_url: str = "https://api.telegram.org/bot{token}/sendMessage"
    timeout: int = 10


@dataclass
class APIConfig:
    """API 端點設定"""
    max_usdt_url: str = "https://max-api.maicoin.com/api/v2/tickers/usdttwd"
    max_btc_url: str = "https://max-api.maicoin.com/api/v2/tickers/btcusdt"
    bot_rate_url: str = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
    yahoo_ticker: str = "TWD=X"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    request_timeout: int = 10
    max_retries: int = 3


# 全域設定實例
usdt_config = USDTConfig()
btc_config = BTCConfig()
telegram_config = TelegramConfig()
api_config = APIConfig()
