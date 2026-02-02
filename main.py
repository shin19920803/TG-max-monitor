import requests
import pandas as pd
import os

# 1. 取得 MAX 交易所 USDT 價格
def get_max_usdt_price():
    try:
        url = "https://max-api.maicoin.com/api/v2/tickers/usdttwd"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        return float(data['last'])
    except Exception as e:
        print(f"❌ MAX 讀取失敗: {e}")
        return None

# 2. 取得 臺灣銀行 [即期賣出] 匯率
def get_bot_usd_rate():
    try:
        url = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
        
        # 讀取網頁表格
        dfs = pd.read_html(url)
        df = dfs[0]
        
        # 臺銀網頁表格欄位索引：
        # [0] 幣別
        # [1] 現金買入
        # [2] 現金賣出
        # [3] 即期買入
        # [4] 即期賣出 <--- 我們要抓這個
        
        # 提取幣別與即期賣出
        df = df.iloc[:, [0, 4]].copy()
        df.columns = ["Currency", "Spot_Sell"]
        
        # 找到包含 "USD" 的那一行
        usd_row = df[df["Currency"].str.contains("USD|美金", na=False)]
        
        if usd_row.empty:
            print("❌ 抓不到美金資料")
            return None
            
        # 取得匯率數值
        rate = usd_row.iloc[0]["Spot_Sell"]
        return float(rate)
        
    except Exception as e:
        print(f"❌ 臺銀網頁讀取失敗: {e}")
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
    print("--- 開始執行監控 (臺銀即期匯率版) ---")
    max_p = get_max_usdt_price()
    bank_p = get_bot_usd_rate()

    if max_p is None or bank_p is None:
        print("數據不足，跳過")
        return

    diff = max_p - bank_p
    rate = (diff / bank_p) * 100
    
    print(f"MAX: {max_p}, 臺銀即期: {bank_p}, 價差: {diff:.2f}")

    # 設定通知門檻 (0.15)
    THRESHOLD = 0.15 

    if diff >= THRESHOLD:
        msg = (
            f"🚨 <b>USDT 搬磚機會 (即期)</b> 🚨\n\n"
            f"💎 <b>MAX:</b> {max_p}\n"
            f"🏦 <b>臺銀即期:</b> {bank_p}\n"
            f"💰 <b>溢價:</b> {diff:.2f} ({rate:.2f}%)"
        )
        send_telegram_msg(msg)
    else:
        print(f"未達 {THRESHOLD} 門檻，不通知")

if __name__ == "__main__":
    monitor()
