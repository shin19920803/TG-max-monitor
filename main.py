import requests
import pandas as pd
import os

# 1. 取得 MAX 交易所 USDT 價格
def get_max_usdt_price():
    try:
        url = "https://max-api.maicoin.com/api/v2/tickers/usdttwd"
        headers = {"User-Agent": "Mozilla/5.0"}
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
        dfs = pd.read_html(url)
        df = dfs[0]
        df = df.iloc[:, [0, 4]].copy()
        df.columns = ["Currency", "Spot_Sell"]
        usd_row = df[df["Currency"].str.contains("USD|美金", na=False)]
        if usd_row.empty: return None
        return float(usd_row.iloc[0]["Spot_Sell"])
    except Exception as e:
        print(f"❌ 臺銀讀取失敗: {e}")
        return None

# 3. 發送 Telegram 通知 (自動除錯修正版)
def send_telegram_msg(message):
    # 【關鍵修正】加上 .strip() 自動刪除前後空白與換行
    token = os.environ.get("TG_TOKEN", "").strip()
    chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        print("❌ 錯誤：找不到 Token 或 Chat ID")
        return

    # 印出來檢查修正後的長度 (應該會變回 46)
    # print(f"🔍 修正後 Token 長度: {len(token)}") 

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ Telegram 通知已發送成功！")
        else:
            print(f"❌ 發送失敗 (HTTP {r.status_code}): {r.text}")
    except Exception as e:
        print(f"⚠️ 連線錯誤: {e}")

# 主程式
def monitor():
    print("--- 開始執行 (含自動修正) ---")
    max_p = get_max_usdt_price()
    bank_p = get_bot_usd_rate()

    if max_p is None or bank_p is None:
        print("數據不足，跳過")
        return

    diff = max_p - bank_p
    rate = (diff / bank_p) * 100
    
    print(f"MAX: {max_p}, 臺銀: {bank_p}, 價差: {diff:.2f}")

    # 設定門檻
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
