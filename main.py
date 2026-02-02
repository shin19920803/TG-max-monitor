import requests
import pandas as pd
import os

# 1. 取得 MAX 交易所 USDT 價格
def get_max_usdt_price():
    try:
        url = "https://max-api.maicoin.com/api/v3/public/tickers/usdttwd"
        # 設定 timeout 避免卡死
        res = requests.get(url, timeout=10).json()
        return float(res['last'])
    except Exception as e:
        print(f"❌ 讀取 MAX 失敗: {e}")
        return None

# 2. 取得臺灣銀行美金現金賣出價
def get_bot_usd_rate():
    try:
        # 臺銀 CSV 下載點
        csv_url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
        df = pd.read_csv(csv_url)
        
        # 篩選幣別為 USD
        usd_row = df[df['幣別'] == 'USD']
        
        # 取得「本行現金賣出」欄位
        cash_sell_rate = usd_row['本行現金賣出'].values[0]
        return float(cash_sell_rate)
    except Exception as e:
        print(f"❌ 讀取臺銀失敗: {e}")
        return None

# 3. 發送 Telegram 通知
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ 錯誤：找不到 Telegram 設定 (Secrets)")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML" # 支援 HTML 格式 (粗體等)
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ 通知發送成功")
        else:
            print(f"⚠️ 發送失敗: {r.text}")
    except Exception as e:
        print(f"⚠️ 連線錯誤: {e}")

# 主邏輯
def monitor():
    print("--- 開始執行監控 ---")
    max_price = get_max_usdt_price()
    bank_price = get_bot_usd_rate()

    if max_price is None or bank_price is None:
        print("數據不足，結束程式")
        return

    # 計算溢價
    diff = max_price - bank_price
    rate = (diff / bank_price) * 100

    print(f"MAX: {max_price}, Bank: {bank_price}, Diff: {diff:.2f}")

    # 判斷是否發送通知 (溢價 >= 0.2)
    if diff >= 0.2:
        # 使用 HTML 語法美化訊息
        msg = (
            f"🚨 <b>USDT 搬磚機會出現</b> 🚨\n\n"
            f"💎 <b>MAX 價格:</b> {max_price} TWD\n"
            f"🏦 <b>臺銀現金:</b> {bank_price} TWD\n"
            f"--------------------------\n"
            f"💰 <b>溢價金額:</b> {diff:.2f} 元\n"
            f"📈 <b>溢價幅度:</b> {rate:.2f}%"
        )
        send_telegram_msg(msg)
    else:
        print(f"目前溢價僅 {diff:.2f}，未達 0.2 門檻，不打擾。")

if __name__ == "__main__":
    monitor()
