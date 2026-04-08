"""
USDT 搬磚監控模組
監控 MAX 交易所與銀行匯率的價差機會
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import usdt_config
from utils.logger import get_logger
from utils.data_fetcher import get_max_usdt_price, get_usd_rate_with_fallback, BankRate
from utils.telegram import send_usdt_alert

logger = get_logger("tg_monitor.usdt")


class USDTMonitor:
    """USDT 搬磚監控器"""
    
    def __init__(self):
        self.config = usdt_config
        self.state_file = self.config.state_file
    
    def _is_weekend(self) -> bool:
        """檢查是否為週末"""
        tw_time = datetime.utcnow() + timedelta(hours=8)
        return tw_time.weekday() >= 5
    
    def _load_last_diff(self) -> float:
        """讀取上次的價差"""
        if not os.path.exists(self.state_file):
            return 0.0
        
        try:
            with open(self.state_file, "r") as f:
                return float(f.read().strip())
        except (ValueError, IOError) as e:
            logger.warning(f"讀取狀態檔案失敗: {e}")
            return 0.0
    
    def _save_diff(self, diff: float) -> None:
        """儲存當前價差"""
        try:
            with open(self.state_file, "w") as f:
                f.write(str(diff))
        except IOError as e:
            logger.error(f"儲存狀態檔案失敗: {e}")
    
    def _calculate_spread(self, max_price: float, bank_sell: float) -> tuple:
        """計算價差與溢價率"""
        diff = max_price - bank_sell
        rate = (diff / bank_sell) * 100
        return diff, rate
    
    def _should_notify(self, diff: float, last_diff: float) -> bool:
        """判斷是否應該發送通知"""
        # 未達門檻
        if diff < self.config.threshold:
            logger.info(f"價差 {diff:.2f} 未達門檻 {self.config.threshold}")
            return False
        
        # 變動幅度過小
        change = abs(diff - last_diff)
        if change <= self.config.change_threshold and last_diff >= self.config.threshold:
            logger.info(f"變動幅度 {change:.3f} 過小，跳過通知")
            return False
        
        return True
    
    def run(self) -> bool:
        """執行 USDT 監控"""
        logger.info("--- 執行 USDT 監控 (以即期賣出為基準) ---")
        
        # 取得 MAX 價格
        max_price = get_max_usdt_price()
        if max_price is None:
            logger.error("無法取得 MAX USDT 價格")
            return False
        
        # 取得銀行匯率
        is_weekend = self._is_weekend()
        bank_rate: Optional[BankRate] = get_usd_rate_with_fallback(is_weekend)
        
        if bank_rate is None:
            logger.error("無法取得銀行匯率")
            return False
        
        # 計算價差
        diff, rate = self._calculate_spread(max_price, bank_rate.sell)
        logger.info(
            f"MAX: {max_price}, "
            f"賣出基準: {bank_rate.sell:.2f} ({bank_rate.source}), "
            f"價差: {diff:.2f} ({rate:.2f}%)"
        )
        
        # 載入上次狀態
        last_diff = self._load_last_diff()
        
        # 儲存當前狀態
        self._save_diff(diff)
        
        # 判斷是否通知
        if not self._should_notify(diff, last_diff):
            return True
        
        # 發送通知
        logger.info(f"🚨 發現搬磚機會！價差: {diff:.2f}")
        send_usdt_alert(
            max_price=max_price,
            bank_sell=bank_rate.sell,
            bank_buy=bank_rate.buy,
            source_name=bank_rate.source,
            diff=diff,
            rate=rate
        )
        
        return True


def monitor_usdt() -> bool:
    """執行 USDT 監控（向後相容的函式介面）"""
    monitor = USDTMonitor()
    return monitor.run()


if __name__ == "__main__":
    from utils.logger import setup_logger
    setup_logger()
    monitor_usdt()
