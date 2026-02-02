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

# 3. 發送 Telegram 通知 (強力除錯版)
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    
    # 檢查 Token 是否有讀取到 (隱藏中間內容)
    if token:
        print(f"🔍 檢查 Token: {token[:5]}...{token[-5:]} (長度: {len(token)})")
    else:
        print("❌ 嚴重錯誤：程式讀取不到 TG_TOKEN！")

    if chat_id:
        print(f"🔍 檢查 Chat ID: {chat_id}")
    else:
        print("❌ 嚴重錯誤：程式讀取不到 TG_CHAT_ID！")

    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        
        # 【關鍵修改】檢查回傳狀態碼
        if r.status_code == 200:
            print("✅ Telegram 回應成功：訊息已送達！")
        else:
            print("---------------------------------------")
            print(f"❌ 發送失敗！HTTP 狀態碼: {r.status_code}")
            print(f"❌ 錯誤原因: {r.text}")  # 這行會告訴我們真正的兇手
            print("---------------------------------------")
            
    except Exception as e:
        print(f"⚠️ 連線錯誤: {e}")

# 主程式
def monitor():
    print("--- 開始執行診斷模式 ---")
    max_p = get_max_usdt_price()
    bank_p = get_bot_usd_rate()

    if max_p is None or bank_p is None:
        print("數據不足，跳過")
        return

    diff = max_p - bank_p
    rate = (diff / bank_p) * 100
    
    print(f"MAX: {max_p}, 臺銀: {bank_p}, 價差: {diff:.2f}")

    # 強制發送測試訊息，不管溢價多少
    print("🚀 嘗試發送測試訊息...")
    msg = (
        f"🛠 <b>連線測試</b> 🛠\n"
        f"看到這則訊息代表設定成功！\n"
        f"目前溢價: {diff:.2f}"
    )
    send_telegram_msg(msg)

if __name__ == "__main__":
    monitor()
