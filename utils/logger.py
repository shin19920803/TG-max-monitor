"""
日誌模組
提供統一的日誌格式與管理
"""
import logging
import sys
from datetime import datetime, timedelta


def get_taiwan_time() -> str:
    """取得台灣時間字串"""
    return (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')


class TaiwanTimeFormatter(logging.Formatter):
    """使用台灣時間的日誌格式化器"""
    
    def formatTime(self, record, datefmt=None):
        return get_taiwan_time()


def setup_logger(name: str = "tg_monitor", level: int = logging.INFO) -> logging.Logger:
    """
    設定並返回 logger
    
    Args:
        name: logger 名稱
        level: 日誌等級
    
    Returns:
        設定好的 logger 實例
    """
    logger = logging.getLogger(name)
    
    # 避免重複添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 格式設定
    formatter = TaiwanTimeFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = "tg_monitor") -> logging.Logger:
    """取得已存在的 logger 或建立新的"""
    return logging.getLogger(name)
