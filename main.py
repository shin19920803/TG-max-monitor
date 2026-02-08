import requests
import pandas as pd
import os
import json
import time
import yfinance as yf # 引入 Yahoo 財經套件
from datetime import datetime, timedelta

# ===========================
# 🟢 設定區
# ===========================

# 1. USDT 監控設定
USDT_THRESHOLD = 0.2          # 溢價門檻
USDT_CHANGE_THRESHOLD = 0     # 變動通知門檻
USDT_STATE_FILE = "last_state.txt"
BANK_SPREAD_FIX = 0.12        # 【關鍵】Yahoo只有中間價，我們要手動加 0.12 當作銀行賣出的手續費

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
# 💰 功能 1: USDT 搬磚監控 (雙軌制)
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

# 來源 A: 台灣銀行 (優先)
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
        print(f"⚠️ 台銀讀取失敗 (可能維修中): {e}")
        return None

# 來源 B: Yahoo Finance (備用)
def get_yahoo_usd_rate():
    try:
        # TWD=X 代表 USD/TWD 匯率
        ticker = yf.Ticker("TWD=X")
        # 抓取最近 1 分鐘的即時資料
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            # 如果抓不到 1 分鐘，改抓日線最後一盤
            data = ticker.history(period="1d")
        
        last_price = data['Close'].iloc[-1]
        
        # 【重要修正】Yahoo 給的是中間價，必須加上銀行點差
        # 假設銀行賣出價比中間價貴 0.12 (保守估計)
        estimated_bank_sell = last_price + BANK_SPREAD_FIX
        
        return estimated_bank_sell, last_price
    except Exception as e:
        print(f"❌ Yahoo 財經讀取失敗: {e}")
        return None, None

def monitor_usdt():
    print("--- [1] 執行 USDT 監控 (雙軌制) ---")
    max_p = get_max_usdt_price()
    
    # 策略：先抓台銀，失敗才抓 Yahoo
    bank_p = get_bot_usd_rate()
    source_name = "臺銀即期"
    
    # 如果台銀抓不到，或者你想在非營業時間強制用 Yahoo (可自行調整邏輯)
    if bank_p is None:
        print("⚠️ 無法取得台銀匯率，切換至 Yahoo Finance 備援模式...")
        estimated_p, raw_p = get_yahoo_usd_rate()
        
        if estimated_p is not None:
            bank_p = estimated_p
            source_name = f"Yahoo估算 (原{raw_p:.2f}+{BANK_SPREAD_FIX})"
        else:
            print("❌ 所有匯率來源都失敗，跳過本次監控")
            return

    if max_p is None:
        print("MAX 數據不足，跳過")
        return

    diff = max_p - bank_p
    rate = (diff / bank_p) * 100
    
    print(f"MAX: {max_p}, 成本基準({source_name}): {bank_p:.2f}, 價差: {diff:.2f}")

    # 讀取上次狀態
    last_diff = 0.0
    if os.path.exists(USDT_STATE_FILE):
        try:
            with open(USDT_STATE_FILE, "r") as f:
                last_diff = float(f.read().strip())
        except:
            pass

    # 儲存這次狀態
    with open(USDT_STATE_FILE, "w") as f:
        f.write(str(diff))

    if diff < USDT_THRESHOLD:
        print(f"未達 {USDT_THRESHOLD} 門檻")
        return

    change = abs(diff - last_diff)
    if change <= USDT_CHANGE_THRESHOLD and last_diff >= USDT_THRESHOLD:
        print(f"變動幅度 {change:.3f} 過小，跳過通知")
        return

    msg = (
        f"🚨 <b>USDT 搬磚機會</b> 🚨\n\n"
        f"💎 <b>MAX:</b> {max_p}\n"
        f"🏦 <b>成本基準:</b> {bank_p:.2f} ({source_name})\n"
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
    else:
        print("⚠️ 找不到歷史檔案")

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
