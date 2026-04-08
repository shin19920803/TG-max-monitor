"""
BTC 暴跌監控模組
監控 BTC/USDT 價格在指定時間窗口內的跌幅
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import btc_config
from utils.logger import get_logger, get_taiwan_time
from utils.data_fetcher import get_btc_price
from utils.telegram import send_btc_alert

logger = get_logger("tg_monitor.btc")


class BTCMonitor:
    """BTC 暴跌監控器"""
    
    def __init__(self):
        self.config = btc_config
        self.history_file = self.config.history_file
    
    def _load_history(self) -> List:
        """載入價格歷史"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"讀取歷史檔案失敗: {e}")
            return []
    
    def _save_history(self, history: List) -> None:
        """儲存價格歷史"""
        try:
            with open(self.history_file, "w") as f:
                json.dump(history, f)
        except IOError as e:
            logger.error(f"儲存歷史檔案失敗: {e}")
    
    def _cleanup_history(self, history: List, current_time: float) -> List:
        """清理過期的歷史資料"""
        cutoff_time = current_time - self.config.time_window
        return [x for x in history if x[0] > cutoff_time]
    
    def _calculate_drop_rate(self, current_price: float, history: List) -> Tuple[float, float]:
        """計算跌幅"""
        if not history:
            return 0.0, current_price
        
        max_price = max(x[1] for x in history)
        drop_rate = (max_price - current_price) / max_price
        
        return drop_rate, max_price
    
    def run(self) -> bool:
        """執行 BTC 監控"""
        time_str = get_taiwan_time()
        logger.info(f"--- 執行 BTC/USDT 暴跌監控 (門檻 {self.config.drop_threshold*100}%) ---")
        logger.info(f"執行時間 (台灣): {time_str}")
        
        # 取得當前價格
        current_price = get_btc_price()
        if current_price is None:
            logger.error("無法取得 BTC 價格")
            return False
        
        now = time.time()
        
        # 載入並清理歷史
        history = self._load_history()
        history = self._cleanup_history(history, now)
        
        # 加入當前價格
        history.append([now, current_price])
        
        # 儲存歷史
        self._save_history(history)
        
        # 計算跌幅
        drop_rate, max_price_1h = self._calculate_drop_rate(current_price, history)
        
        logger.info(f"目前 BTC: {current_price:,.2f} USDT")
        logger.info(f"1H內最高: {max_price_1h:,.2f} USDT")
        logger.info(f"跌幅: {drop_rate*100:.2f}% (門檻: {self.config.drop_threshold*100}%)")
        
        # 判斷是否達到警報門檻
        if drop_rate >= self.config.drop_threshold:
            logger.warning(f"📉 BTC 急跌警報！跌幅: {drop_rate*100:.2f}%")
            send_btc_alert(
                drop_rate=drop_rate,
                current_price=current_price,
                max_price_1h=max_price_1h,
                time_str=time_str
            )
        else:
            logger.info("未達暴跌門檻，安全。")
        
        return True


def monitor_btc() -> bool:
    """執行 BTC 監控（向後相容的函式介面）"""
    monitor = BTCMonitor()
    return monitor.run()


if __name__ == "__main__":
    from utils.logger import setup_logger
    setup_logger()
    monitor_btc()
