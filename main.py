import requests
import yfinance as yf # 引入 Yahoo 財經工具
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

# 2. 取得 美金匯率 (Yahoo Finance / 類似 Google 匯率)
def get_usd_rate():
    try:
        # 抓取 USDTWD=X (美金兌台幣匯率)
        # period="1d" 代表抓取最近一天的資料
        ticker = yf.Ticker("USDTWD=X")
        data = ticker.history(period="1d")
        
        if data.empty:
            print("❌ Yahoo Finance 抓不到資料")
            return None
            
        # 取得最新的收盤價 (Close)
        rate = data['Close'].iloc[-1]
        
        # 四捨五入到小數點第二位
        return round(float(rate), 2)
    except Exception as e:
        print(f"❌ 匯率讀取失敗: {e}")
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
    print("--- 開始執行監控 (Yahoo版) ---")
    max_p = get_max_usdt_price()
    usd_p = get_usd_rate()

    if max_p is None or usd_p is None:
        print("數據不足，跳過")
        return

    diff = max_p - usd_p
    rate = (diff / usd_p) * 100
    
    print(f"MAX: {max_p}, USD匯率: {usd_p}, 價差: {diff:.2f}")

    # 判斷溢價 (建議門檻稍微調高，因為 Yahoo 匯率通常比銀行賣出價低)
    # 這裡我先幫你設成 0.3，你可以自己改回 0.2
    THRESHOLD = 0.3 

    if diff >= THRESHOLD:
        msg = (
            f"🚨 <b>USDT 搬磚機會</b> 🚨\n\n"
            f"💎 <b>MAX:</b> {max_p}\n"
            f"🇺🇸 <b>美金:</b> {usd_p} (Yahoo)\n"
            f"💰 <b>溢價:</b> {diff:.2f} ({rate:.2f}%)"
        )
        send_telegram_msg(msg)
    else:
        print(f"未達 {THRESHOLD} 門檻，不通知")

if __name__ == "__main__":
    monitor()
