# 🚀 TG MAX Monitor

> USDT 搬磚價差監控 + BTC 暴跌警報，自動推送到 Telegram

---

## ✨ 功能特色

### 💰 USDT 搬磚監控
- 監控 MAX 交易所 USDT/TWD 價格
- 對比台灣銀行即期匯率，計算套利空間
- 週末自動切換至 Yahoo Finance 作為匯率來源
- 可自訂價差門檻，超過時自動通知

### 📉 BTC 暴跌警報
- 監控 BTC/USDT 價格變化
- 追蹤 1 小時內的價格走勢
- 跌幅超過門檻時即時警報（預設 1%）

---

## 🛠 專案結構
TG-max-monitor/
├── main.py              # 主程式入口
├── config.py            # 設定管理
├── requirements.txt     # 依賴套件
├── utils/
│   ├── telegram.py      # Telegram 通知
│   ├── data_fetcher.py  # API 資料抓取
│   └── logger.py        # 日誌管理
├── monitors/
│   ├── usdt_monitor.py  # USDT 監控邏輯
│   └── btc_monitor.py   # BTC 監控邏輯
└── .github/workflows/   # GitHub Actions
---

## 🚀 快速開始

### 使用 GitHub Actions（自動執行）

1. **Fork 此專案**

2. **設定 GitHub Secrets**
   
   進入 `Settings` → `Secrets and variables` → `Actions`，新增：
   
   | Name | Description |
   |------|-------------|
   | `TG_TOKEN` | Telegram Bot Token |
   | `TG_CHAT_ID` | 接收通知的 Chat ID |

3. **完成！** 機器人會每 5 分鐘自動執行

---

## ⚙️ 環境變數設定

| 變數名稱 | 預設值 | 說明 |
|---------|-------|------|
| `TG_TOKEN` | - | Telegram Bot Token（必填） |
| `TG_CHAT_ID` | - | Telegram Chat ID（必填） |
| `USDT_THRESHOLD` | `0.2` | USDT 價差通知門檻 |
| `BTC_DROP_THRESHOLD` | `0.01` | BTC 跌幅門檻（1%） |

---

## 📱 通知範例

### USDT 搬磚機會
### BTC 急跌警報
---

## 📄 授權

MIT License

---

## ⚠️ 免責聲明

本專案僅供學習與參考，不構成任何投資建議。加密貨幣交易具有高風險，請自行評估。
