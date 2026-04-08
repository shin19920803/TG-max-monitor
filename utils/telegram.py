"""
Telegram 通知模組
處理所有 Telegram Bot API 相關功能
"""
import requests
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import telegram_config
from utils.logger import get_logger

logger = get_logger("tg_monitor.telegram")


class TelegramError(Exception):
    """Telegram API 錯誤"""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, TelegramError))
)
def send_telegram_msg(message: str, parse_mode: str = "HTML") -> bool:
    """
    發送 Telegram 訊息
    
    Args:
        message: 要發送的訊息內容
        parse_mode: 解析模式 (HTML 或 Markdown)
    
    Returns:
        發送是否成功
    
    Raises:
        TelegramError: 當發送失敗時
    """
    token = telegram_config.token
    chat_id = telegram_config.chat_id
    
    if not token or not chat_id:
        logger.error("❌ 錯誤：找不到 TG_TOKEN 或 TG_CHAT_ID 環境變數")
        return False
    
    url = telegram_config.api_url.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            timeout=telegram_config.timeout
        )
        response.raise_for_status()
        
        result = response.json()
        if not result.get("ok"):
            raise TelegramError(f"Telegram API 回傳錯誤: {result}")
        
        logger.info("✅ Telegram 通知已發送")
        return True
        
    except requests.RequestException as e:
        logger.error(f"⚠️ 發送失敗: {e}")
        raise


def send_usdt_alert(
    max_price: float,
    bank_sell: float,
    bank_buy: float,
    source_name: str,
    diff: float,
    rate: float
) -> bool:
    """
    發送 USDT 搬磚機會警報
    """
    msg = (
        f"🚨 <b>USDT 搬磚機會</b> 🚨\n\n"
        f"💎 <b>MAX:</b> {max_price}\n"
        f"🏦 <b>銀行賣出 (成本/基準):</b> {bank_sell:.2f}\n"
        f"🏦 <b>銀行買入 (參考):</b> {bank_buy:.2f}\n"
        f"ℹ️ <b>來源:</b> {source_name}\n"
        f"💰 <b>溢價:</b> {diff:.2f} ({rate:.2f}%)"
    )
    return send_telegram_msg(msg)


def send_btc_alert(
    drop_rate: float,
    current_price: float,
    max_price_1h: float,
    time_str: str
) -> bool:
    """
    發送 BTC 暴跌警報
    """
    msg = (
        f"📉 <b>BTC/USDT 急跌警報</b> 📉\n\n"
        f"🔻 <b>1H內跌幅:</b> {drop_rate*100:.2f}%\n"
        f"💵 <b>目前價格:</b> {current_price:,.2f} USDT\n"
        f"🏔 <b>1H內最高:</b> {max_price_1h:,.2f} USDT\n"
        f"⏰ <b>時間:</b> {time_str}"
    )
    return send_telegram_msg(msg)
