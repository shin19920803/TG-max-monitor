import requests
import pandas as pd
import os

# 1. 取得 MAX 交易所 USDT 價格 (使用 V2 API)
def get_max_usdt_price():
    try:
        url = "https://max-api.maicoin.com/api/v2/tickers/usdttwd"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        return float(data['last'])
    except Exception as e:
        print(f"❌ MAX 讀取失敗: {e}")
        return None

# 2. 取得臺灣銀行美金現金賣出價 (修正編碼問題)
def get_bot_usd_rate():
    try:
        csv_url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
        
        # 【關鍵修正】加上 encoding='cp950' 讓它能讀懂繁體中文
        # 並且指定 header=0 確保正確讀取標題
        df = pd.read_csv(csv_url, encoding='cp950')
        
        # 為了保險起見，我們不依賴欄位名稱 (怕它改版)，我們直接抓「位置」
        # 第 0 欄通常是幣別 (例如: "USD  美金")
        # 找出包含 "USD" 的那一行
        usd_row = df[df.iloc[:, 0].str.contains('USD', na=False)]
        
        if usd_row.empty:
            print(f"❌ 在表中找不到 USD 資料。讀到的前幾筆幣別: {df.iloc[:3, 0].values}")
            return None
            
        # 根據臺銀 CSV 格式：第 2 欄 (索引 2) 是「本行現金賣出」
        # (第0欄=幣別, 第1欄=現金買入, 第2欄=現金賣出)
        cash_sell_rate = usd_row.iloc[0, 2]
        
        return float(cash_sell_rate)
    except Exception as e:
        print(f"❌ 臺銀讀取失敗: {e}")
        return None

# 3. 發送 Telegram 通知
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ 錯誤：找不到 Telegram 設定")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print("✅ 通知已發送")
    except Exception as e:
        print(f"⚠️ 發送失敗: {e}")

# 主程式
def monitor():
    print("--- 開始執行監控 ---")
    max_p = get_max_usdt_price()
    bot_p = get_bot_usd_rate()

    if max_p is None or bot_p is None:
        print("數據不足，跳過本次執行")
        return

    diff = max_p - bot_p
    rate = (diff / bot_p) * 100
    
    print(f"MAX: {max_p}, 臺銀: {bot_p}, 價差: {diff:.2f}")

    # 判斷溢價是否 >= 0.2
    if diff >= 0.2:
        msg = (
            f"🚨 <b>USDT 搬磚機會</b> 🚨\n\n"
            f"💎 <b>MAX:</b> {max_p}\n"
            f"🏦 <b>臺銀:</b> {bot_p}\n"
            f"💰 <b>溢價:</b> {diff:.2f} ({rate:.2f}%)"
        )
        send_telegram_msg(msg)
    else:
        print("未達 0.2 門檻，不通知")

if __name__ == "__main__":
    monitor()
