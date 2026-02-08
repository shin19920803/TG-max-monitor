import requests
import pandas as pd
import os
import json
import time
import yfinance as yf
from datetime import datetime, timedelta

# ===========================
# 🟢 設定區
# ===========================

# 1. USDT 監控設定
USDT_THRESHOLD = 0.2          # 溢價門檻
USDT_CHANGE_THRESHOLD = 0     # 變動通知門檻
USDT_STATE_FILE = "last_state.txt"
BANK_SPREAD_FIX = 0.12        # Yahoo中間價 + 0.12 = 預估銀行賣出價

# 2. BTC 監控設定 (1%)
BTC_DROP_THRESHOLD = 0.01     
BTC_TIME_WINDOW = 3600
BTC_HISTORY_FILE = "btc_history.json"

# ===========================
# 🛠 工具函式
# ===========================

def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN", "").replace(" ", "").replace("\n", "").strip()
    chat_id = os.environ.get("TG_CHAT_ID", "").replace(" ", "").replace("\n", "").strip()
    
    if not token or not chat_id:
        print("❌ 錯誤：找不到 Token 或 Chat ID")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
        print("✅ Telegram 通知已發送")
    except Exception as e:
        print(f"⚠️ 發送失敗: {e}")

# ===========================
# 💰 功能 1: USDT 搬磚監控 (含週末判斷)
# ===========================

def get_max_usdt_price():
    try:
        url = "https://max-api.maicoin.com/api/v2/tickers/usdttwd"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        return float(data['last'])
    except Exception as e:
        print(f"❌ MAX USDT 讀取失敗: {e}")
        return None

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
        print(f"⚠️ 台銀讀取失敗: {e}")
        return None

def get_yahoo_usd_rate():
    try:
        # TWD=X 代表 USD/TWD 匯率
        ticker = yf.Ticker("TWD=X")
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            data = ticker.history(period="1d")
        
        last_price = data['Close'].iloc[-1]
        
        # 加上預估的銀行點差
        estimated_bank_sell = last_price + BANK_SPREAD_FIX
        return estimated_bank_sell, last_price
    except Exception as e:
        print(f"❌ Yahoo 財經讀取失敗: {e}")
        return None, None

def monitor_usdt():
    print("--- [1] 執行 USDT 監控 (週末智慧版) ---")
    
    # 1. 判斷今天是不是週末 (台灣時間)
    tw_time = datetime.utcnow() + timedelta(hours=8)
    weekday = tw_time.weekday() # 0=週一 ... 5=週六, 6=週日
    
    max_p = get_max_usdt_price()
    bank_p = None
    source_name = ""

    # 2. 決定要抓哪裡的匯率
    if weekday >= 5: # 如果是週六(5) 或 週日(6)
        print(f"📅 檢測到今天是週末 (星期{weekday+1})，強制切換至 Yahoo 財經...")
        estimated_p, raw_p = get_yahoo_usd_rate()
        if estimated_p:
            bank_p = estimated_p
            source_name = f"Yahoo估算 (原{raw_p:.2f}+{BANK_SPREAD_FIX})"
    else:
        # 平日優先抓台銀
        bank_p = get_bot_usd_rate()
        source_name = "臺銀即期"
        
        # 如果平日台銀掛掉，也備援用 Yahoo
        if bank_p is None:
            print("⚠️ 台銀讀取失敗，轉用 Yahoo...")
            estimated_p, raw_p = get_yahoo_usd_rate()
            if estimated_p:
                bank_p = estimated_p
                source_name = f"Yahoo估算 (原{raw_p:.2f}+{BANK_SPREAD_FIX})"

    if max_p is None or bank_p is None:
        print("❌ 數據不足，跳過本次監控")
        return

    diff = max_p - bank_p
    rate = (diff / bank_p) * 100
    
    print(f"MAX: {max_p}, 成本基準: {bank_p:.2f} ({source_name}), 價差: {diff:.2f}")

    # 讀取與儲存狀態
    last_diff = 0.0
    if os.path.exists(USDT_STATE_FILE):
        try:
            with open(USDT_STATE_FILE, "r") as f:
                last_diff = float(f.read().strip())
        except:
            pass

    with open(USDT_STATE_FILE, "w") as f:
        f.write(str(diff))

    # 判斷通知
    if diff < USDT_THRESHOLD:
        print(f"未達 {USDT_THRESHOLD} 門檻")
        return

    change = abs(diff - last_diff)
    if change <= USDT_CHANGE_THRESHOLD and last_diff >= USDT_THRESHOLD:
        print(f"變動幅度 {change:.3f} 過小，跳過通知")
        return

    msg = (
        f"🚨 <b>USDT 搬磚機會 (週末模式)</b> 🚨\n\n"
        f"💎 <b>MAX:</b> {max_p}\n"
        f"🏦 <b>成本基準:</b> {bank_p:.2f}\n"
        f"ℹ️ <b>來源:</b> {source_name}\n"
        f"💰 <b>溢價:</b> {diff:.2f} ({rate:.2f}%)"
    )
    send_telegram_msg(msg)

# ===========================
# 📉 功能 2: BTC/USDT 暴跌監控 (1%)
# ===========================

def get_btc_price():
    try:
        url = "https://max-api.maicoin.com/api/v2/tickers/btcusdt" 
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        return float(data['last'])
    except Exception as e:
        print(f"❌ BTC 讀取失敗: {e}")
        return None

def monitor_btc():
    print("\n--- [2] 執行 BTC/USDT 暴跌監控 (門檻 1%) ---")
    
    current_time_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    print(f"執行時間 (台灣): {current_time_str}")

    current_price = get_btc_price()
    if current_price is None:
        return

    now = time.time()
    history = []

    if os.path.exists(BTC_HISTORY_FILE):
        try:
            with open(BTC_HISTORY_FILE, "r") as f:
                history = json.load(f)
            print(f"成功讀取歷史資料，共 {len(history)} 筆")
        except:
            history = []
    
    history = [x for x in history if x[0] > (now - BTC_TIME_WINDOW)]
    history.append([now, current_price])

    with open(BTC_HISTORY_FILE, "w") as f:
        json.dump(history, f)

    if not history:
        max_price_1h = current_price
    else:
        max_price_1h = max(x[1] for x in history)
    
    drop_rate = (max_price_1h - current_price) / max_price_1h

    print(f"目前 BTC: {current_price} USDT")
    print(f"1H內最高: {max_price_1h} USDT")
    print(f"跌幅: {drop_rate*100:.2f}% (門檻: {BTC_DROP_THRESHOLD*100}%)")

    if drop_rate >= BTC_DROP_THRESHOLD:
        msg = (
            f"📉 <b>BTC/USDT 急跌警報</b> 📉\n\n"
            f"🔻 <b>1H內跌幅:</b> {drop_rate*100:.2f}%\n"
            f"💵 <b>目前價格:</b> {current_price:,.2f} USDT\n"
            f"🏔 <b>1H內最高:</b> {max_price_1h:,.2f} USDT\n"
            f"⏰ <b>時間:</b> {current_time_str}"
        )
        send_telegram_msg(msg)
    else:
        print("未達暴跌門檻，安全。")

if __name__ == "__main__":
    monitor_usdt()
    monitor_btc()
