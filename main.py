import requests
import pandas as pd
import os

# 設定通知門檻 (價差多少以上才開始監控)
THRESHOLD = 0.2
# 設定變動容忍值 (價差變化超過多少才再次通知)
# 例如: 上次是 0.25，這次變 0.26 (差 0.01) -> 不通知
# 例如: 上次是 0.25，這次變 0.30 (差 0.05) -> 通知
CHANGE_THRESHOLD = 0.03

# 檔案名稱 (用來記錄上次的價差)
STATE_FILE = "last_state.txt"

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
        print("✅ Telegram 通知已發送成功！")
    except Exception as e:
        print(f"⚠️ 連線錯誤: {e}")

def get_last_diff():
    """讀取上次的價差"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return float(f.read().strip())
        except:
            return 0.0
    return 0.0

def save_current_diff(diff):
    """儲存這次的價差"""
    with open(STATE_FILE, "w") as f:
        f.write(str(diff))

def monitor():
    print("--- 開始執行監控 (記憶版) ---")
    max_p = get_max_usdt_price()
    bank_p = get_bot_usd_rate()

    if max_p is None or bank_p is None:
        print("數據不足，跳過")
        return

    current_diff = max_p - bank_p
    rate = (current_diff / bank_p) * 100
    
    print(f"MAX: {max_p}, 臺銀: {bank_p}, 價差: {current_diff:.2f}")

    # 1. 先判斷是否達到基本門檻 (例如 0.2)
    if current_diff < THRESHOLD:
        print(f"未達 {THRESHOLD} 門檻，不通知")
        # 即使沒達標，也要更新狀態，這樣下次如果突然跳漲才能捕捉到
        save_current_diff(current_diff) 
        return

    # 2. 判斷跟上次比起來，有沒有顯著變化
    last_diff = get_last_diff()
    change = abs(current_diff - last_diff)

    print(f"上次價差: {last_diff}, 變動幅度: {change:.3f}")

    if change < CHANGE_THRESHOLD:
        print(f"變動幅度小於 {CHANGE_THRESHOLD}，視為無變化，跳過通知")
        return

    # 3. 發送通知並更新記憶
    msg = (
        f"🚨 <b>USDT 價差變動</b> 🚨\n\n"
        f"💎 <b>MAX:</b> {max_p}\n"
        f"🏦 <b>臺銀:</b> {bank_p}\n"
        f"💰 <b>溢價:</b> {current_diff:.2f} ({rate:.2f}%)"
    )
    send_telegram_msg(msg)
    
    # 儲存這次的數值，當作下次的對照組
    save_current_diff(current_diff)

if __name__ == "__main__":
    monitor()
