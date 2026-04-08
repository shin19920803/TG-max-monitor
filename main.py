#!/usr/bin/env python3
"""
TG MAX Monitor - 主程式入口
USDT 搬磚監控 + BTC 暴跌警報
"""

import argparse
import sys

from utils.logger import setup_logger, get_logger
from utils.telegram import send_telegram_msg
from monitors.usdt_monitor import USDTMonitor
from monitors.btc_monitor import BTCMonitor


def parse_args():
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description="TG MAX Monitor - USDT 搬磚監控 + BTC 暴跌警報"
    )
    parser.add_argument("--usdt", action="store_true", help="只執行 USDT 監控")
    parser.add_argument("--btc", action="store_true", help="只執行 BTC 監控")
    parser.add_argument("--test", action="store_true", help="測試模式")
    parser.add_argument("--verbose", "-v", action="store_true", help="顯示詳細日誌")
    
    return parser.parse_args()


def test_mode(logger):
    """測試模式：發送測試訊息"""
    logger.info("🧪 進入測試模式")
    
    test_msg = (
        "🧪 <b>TG MAX Monitor 測試訊息</b> 🧪\n\n"
        "✅ Telegram 連線正常\n"
        "✅ 機器人設定完成\n\n"
        "如果你看到這則訊息，代表一切設定正確！"
    )
    
    success = send_telegram_msg(test_msg)
    
    if success:
        logger.info("✅ 測試訊息發送成功！")
    else:
        logger.error("❌ 測試訊息發送失敗")
        sys.exit(1)


def main():
    """主程式"""
    args = parse_args()
    
    # 設定日誌
    import logging
    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=level)
    logger = get_logger("tg_monitor")
    
    logger.info("=" * 50)
    logger.info("🚀 TG MAX Monitor 啟動")
    logger.info("=" * 50)
    
    # 測試模式
    if args.test:
        test_mode(logger)
        return
    
    # 決定執行哪些監控
    run_usdt = args.usdt or (not args.usdt and not args.btc)
    run_btc = args.btc or (not args.usdt and not args.btc)
    
    success = True
    
    # 執行 USDT 監控
    if run_usdt:
        try:
            usdt_monitor = USDTMonitor()
            if not usdt_monitor.run():
                success = False
        except Exception as e:
            logger.error(f"USDT 監控發生錯誤: {e}")
            success = False
    
    # 執行 BTC 監控
    if run_btc:
        try:
            btc_monitor = BTCMonitor()
            if not btc_monitor.run():
                success = False
        except Exception as e:
            logger.error(f"BTC 監控發生錯誤: {e}")
            success = False
    
    logger.info("=" * 50)
    if success:
        logger.info("✅ 監控完成")
    else:
        logger.warning("⚠️ 部分監控失敗")
    logger.info("=" * 50)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
