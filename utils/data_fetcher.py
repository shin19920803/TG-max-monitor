"""
資料抓取模組
處理所有外部 API 資料獲取
"""
import requests
import pandas as pd
import yfinance as yf
from typing import Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import api_config, usdt_config
from utils.logger import get_logger

logger = get_logger("tg_monitor.data_fetcher")


@dataclass
class BankRate:
    """銀行匯率資料"""
    buy: float  # 買入價
    sell: float  # 賣出價
    source: str  # 來源名稱


class DataFetchError(Exception):
    """資料抓取錯誤"""
    pass


def _get_headers() -> dict:
    """取得 HTTP 請求標頭"""
    return {"User-Agent": api_config.user_agent}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def get_max_usdt_price() -> Optional[float]:
    """
    從 MAX 交易所取得 USDT/TWD 價格
    """
    try:
        response = requests.get(
            api_config.max_usdt_url,
            headers=_get_headers(),
            timeout=api_config.request_timeout
        )
        response.raise_for_status()
        data = response.json()
        price = float(data['last'])
        logger.info(f"MAX USDT 價格: {price}")
        return price
    except requests.RequestException as e:
        logger.error(f"❌ MAX USDT 讀取失敗: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"❌ MAX USDT 資料解析失敗: {e}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def get_bot_usd_rate() -> Optional[BankRate]:
    """
    從台灣銀行取得美元匯率
    """
    try:
        dfs = pd.read_html(api_config.bot_rate_url)
        df = dfs[0]
        
        # 台銀欄位: 0=幣別, 1=現金買入, 2=現金賣出, 3=即期買入, 4=即期賣出
        df = df.iloc[:, [0, 3, 4]].copy()
        df.columns = ["Currency", "Spot_Buy", "Spot_Sell"]
        
        usd_row = df[df["Currency"].str.contains("USD|美金", na=False)]
        if usd_row.empty:
            logger.warning("⚠️ 找不到美元匯率資料")
            return None
        
        buy_rate = float(usd_row.iloc[0]["Spot_Buy"])
        sell_rate = float(usd_row.iloc[0]["Spot_Sell"])
        
        logger.info(f"台銀即期匯率 - 買入: {buy_rate}, 賣出: {sell_rate}")
        return BankRate(buy=buy_rate, sell=sell_rate, source="臺銀即期")
        
    except requests.RequestException as e:
        logger.error(f"⚠️ 台銀讀取失敗: {e}")
        raise
    except Exception as e:
        logger.error(f"⚠️ 台銀資料解析失敗: {e}")
        return None


def get_yahoo_usd_rate() -> Optional[BankRate]:
    """
    從 Yahoo Finance 取得美元匯率（用於週末或台銀失敗時）
    """
    try:
        ticker = yf.Ticker(api_config.yahoo_ticker)
        data = ticker.history(period="1d", interval="1m")
        
        if data.empty:
            data = ticker.history(period="1d")
        
        if data.empty:
            logger.warning("⚠️ Yahoo Finance 無資料")
            return None
            
        last_price = float(data['Close'].iloc[-1])
        
        # 估算銀行買入與賣出價
        spread = usdt_config.bank_spread_fix
        estimated_buy = last_price - spread
        estimated_sell = last_price + spread
        
        logger.info(f"Yahoo 匯率 - 中間價: {last_price}, 估算買入: {estimated_buy:.2f}, 估算賣出: {estimated_sell:.2f}")
        return BankRate(buy=estimated_buy, sell=estimated_sell, source="Yahoo估算")
        
    except Exception as e:
        logger.error(f"❌ Yahoo Finance 讀取失敗: {e}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def get_btc_price() -> Optional[float]:
    """
    從 MAX 交易所取得 BTC/USDT 價格
    """
    try:
        response = requests.get(
            api_config.max_btc_url,
            headers=_get_headers(),
            timeout=api_config.request_timeout
        )
        response.raise_for_status()
        data = response.json()
        price = float(data['last'])
        logger.info(f"MAX BTC 價格: {price} USDT")
        return price
    except requests.RequestException as e:
        logger.error(f"❌ BTC 讀取失敗: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"❌ BTC 資料解析失敗: {e}")
        return None


def get_usd_rate_with_fallback(is_weekend: bool = False) -> Optional[BankRate]:
    """
    取得美元匯率，支援自動 fallback
    """
    if is_weekend:
        logger.info("📅 週末模式，使用 Yahoo Finance")
        return get_yahoo_usd_rate()
    
    # 平日：先嘗試台銀
    try:
        rate = get_bot_usd_rate()
        if rate:
            return rate
    except Exception:
        pass
    
    # Fallback 到 Yahoo
    logger.info("⚠️ 台銀讀取失敗，轉用 Yahoo Finance")
    return get_yahoo_usd_rate()
