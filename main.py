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

# 2. 取得 臺灣銀行 現金賣出匯率 (HTML 表格讀取法)
def get_bot_usd_rate():
    try:
        url = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
        
        # 使用 pandas 直接讀取網頁中的表格
        #這會回傳一個列表，通常匯率表是第一個 [0]
        dfs = pd.read_html(url)
        df = dfs[0]
        
        # 整理欄位：我們只需要前幾欄
        # 臺銀網頁表格格式：
        # 第0欄: 幣別 (Currency)
        # 第1欄: 現金買入
        # 第2欄: 現金賣出 (這是我們要的)
        
        # 複製一份以免跳出警告
        df = df.iloc[:, [0, 2]].copy()
        
        # 設定欄位名稱方便操作
        df.columns = ["Currency", "Cash_Sell"]
        
        # 找到包含 "USD" 或 "美金" 的那一行
        usd_row = df[df["Currency"].str.contains("USD|美金", na=False)]
        
        if usd_row.empty:
            print("❌ 抓不到美金資料")
            return None
            
        # 取得匯率數值
        rate = usd_row.iloc[0]["Cash_Sell"]
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
    print("--- 開始執行監控 (臺銀網頁版) ---")
    max_p = get_max_usdt_price()
    bank_p = get_bot_usd_rate()

    if max_p is None or bank_p is None:
        print("數據不足，跳過")
        return

    diff = max_p - bank_p
    rate = (diff / bank_p) * 100
    
    print(f"MAX: {max_p}, 臺銀: {bank_p}, 價差: {diff:.2f}")

    # 設定通知門檻 (價差 0.15)
    THRESHOLD = 0.15 

    if diff >= THRESHOLD:
        msg = (
            f"🚨 <b>USDT 搬磚機會</b> 🚨\n\n"
            f"💎 <b>MAX:</b> {max_p}\n"
            f"🏦 <b>臺銀:</b> {bank_p}\n"
            f"💰 <b>溢價:</b> {diff:.2f} ({rate:.2f}%)"
        )
        send_telegram_msg(msg)
    else:
        print(f"未達 {THRESHOLD} 門檻，不通知")

if __name__ == "__main__":
    monitor()
