import requests
import pandas as pd
import os

# 1. 取得 MAX 交易所 USDT 價格 (修正為 V2 API)
def get_max_usdt_price():
    try:
        # 改用 v2 版本，這是目前最穩定的公開接口
        url = "https://max-api.maicoin.com/api/v2/tickers/usdttwd"
        
        # 設定 headers 避免被誤判為機器人
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        res = requests.get(url, headers=headers, timeout=10)
        
        # 檢查是否成功 (狀態碼 200)
        if res.status_code != 200:
            print(f"❌ MAX 回應錯誤: {res.status_code}, 內容: {res.text[:50]}")
            return None
            
        data = res.json()
        
        # 確保 'last' 欄位存在
        if 'last' not in data:
            print(f"❌ MAX 數據格式異常 (找不到 last): {data.keys()}")
            return None
            
        return float(data['last'])
    except Exception as e:
        print(f"❌ 讀取 MAX 失敗: {e}")
        return None

# 2. 取得臺灣銀行美金現金賣出價 (修正為位置鎖定法)
def get_bot_usd_rate():
    try:
        csv_url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
        
        # 讀取 CSV，指定編碼 utf-8，並將第一欄當作索引
        df = pd.read_csv(csv_url, encoding='utf-8')
        
        # 找到幣別是 USD 的那一行
        # 臺銀 CSV 的幣別欄位通常在第 0 欄，且格式為 "USD 美金" 或 "USD"
        # 我們直接用字串包含來篩選
        usd_row = df[df.iloc[:, 0].str.contains('USD', na=False)]
        
        if usd_row.empty:
            print("❌ 找不到 USD 幣別資料")
            return None
            
        # 【關鍵修正】
        # 不要用欄位名稱找，改用「位置 (iloc)」找
        # 根據臺銀格式：第 0 欄=幣別, 第 1 欄=現金買入, 第 2 欄=現金賣出
        cash_sell_rate = usd_row.iloc[0, 2]
        
        return float(cash_sell_rate)
    except Exception as e:
        print(f"❌ 讀取臺銀失敗: {e}")
        # 印出欄位名稱幫助除錯
        # print(f"DEBUG - 欄位列表: {df.columns.tolist() if 'df' in locals() else '讀取失敗'}")
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
        "parse_mode": "HTML"
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
