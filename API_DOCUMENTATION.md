# 📡 K博士投研站 - REST API 文檔

**版本**: v1.0
**日期**: 2026-03-11
**狀態**: ✅ 生產就緒

---

## 📌 概述

本 API 提供 **Markdown 格式的股票分析報告**，支援單一或多個分析區塊的取得，並支援多語言版本。

**基礎 URL**:
```
https://allin.auincap.com/api/markdown
```

（本地開發環境：`http://localhost:5000/api/markdown`）

---

## 🎯 API 端點

### **端點 1️⃣：取得單一分析區塊**

```
GET /api/markdown/<ticker>/<section>[?lang=...]
```

**參數**:
| 參數 | 必需 | 類型 | 說明 | 範例 |
|------|------|------|------|------|
| `ticker` | ✅ | string | 股票代碼 | NVDA, 0700.HK, 601899.SS |
| `section` | ✅ | string | 分析區塊 | biz, finance, exec, call, ta_price, ta_analyst, ta_social |
| `lang` | ❌ | string | 語言代碼 (預設: zh_hk) | zh_hk, zh_cn, en |

**回傳**:
- Content-Type: `text/markdown; charset=utf-8`
- 檔案會自動下載

**HTTP 狀態碼**:
| 狀態碼 | 說明 |
|--------|------|
| 200 | 成功，返回 .md 檔案 |
| 404 | 找不到快取或無效參數 |

**範例**:

```bash
# 取得商業模式分析（繁中）
curl https://allin.auincap.com/api/markdown/NVDA/biz \
  -o NVDA_business_model.md

# 取得財務分析（英文）
curl https://allin.auincap.com/api/markdown/NVDA/finance?lang=en \
  -o NVDA_finance_en.md

# 取得港股分析（簡中）
curl https://allin.auincap.com/api/markdown/0700.HK/biz?lang=zh_cn \
  -o TENCENT_business_cn.md
```

---

### **端點 2️⃣：取得多個分析區塊（合併）**

```
GET /api/markdown/<ticker>[?sections=...&lang=...]
```

**參數**:
| 參數 | 必需 | 類型 | 說明 | 範例 |
|------|------|------|------|------|
| `ticker` | ✅ | string | 股票代碼 | NVDA, 0700.HK |
| `sections` | ❌ | string | 逗號分隔的 section 列表 (預設: 全部) | biz,finance,exec |
| `lang` | ❌ | string | 語言代碼 (預設: zh_hk) | zh_hk, zh_cn, en |

**回傳**:
- Content-Type: `text/markdown; charset=utf-8`
- 合併後的完整 .md 檔案

**範例**:

```bash
# 取得全部分析（所有 sections）
curl https://allin.auincap.com/api/markdown/NVDA \
  -o NVDA_full_report.md

# 取得特定 3 個分析區塊
curl "https://allin.auincap.com/api/markdown/NVDA?sections=biz,finance,exec" \
  -o NVDA_business_financial_exec.md

# 英文版本，指定特定區塊
curl "https://allin.auincap.com/api/markdown/NVDA?sections=biz,finance&lang=en" \
  -o NVDA_en.md
```

---

## 📋 分析區塊（Sections）列表

| Section | 英文名稱 | 說明 |
|---------|---------|------|
| `biz` | Business Model Analysis | 商業模式分析 |
| `finance` | Financial Analysis | 財務分析 |
| `exec` | Executive Assessment | 管理層評估 |
| `call` | Earnings Call Insights | 會議展望 |
| `ta_price` | Technical Analysis - Price | 技術面分析（價格） |
| `ta_analyst` | Technical Analysis - Analyst Forecast | 技術面分析（分析師預測） |
| `ta_social` | Technical Analysis - Social Sentiment | 技術面分析（社群情緒） |

---

## 🌐 支援的股票代碼格式

| 市場 | 格式 | 範例 |
|------|------|------|
| 美股 | 字母 | AAPL, NVDA, MSFT |
| 美股（特殊） | 字母.字母 | BRK.B |
| 港股 | 4-5位數字.HK | 0700.HK, 09618.HK |
| A股 | 6位數字.SS / .SZ | 601899.SS, 000858.SZ |

---

## 🗣️ 支援的語言

| 語言代碼 | 語言 | 說明 |
|---------|------|------|
| `zh_hk` | 繁體中文 | 預設語言 |
| `zh_cn` | 簡體中文 | 簡體版本 |
| `en` | English | 英文版本 |

---

## 💡 使用案例

### **場景 1：定期下載分析報告**

```bash
#!/bin/bash

# 每天早上 09:00 自動下載最新分析
TICKERS=("NVDA" "AAPL" "0700.HK")

for ticker in "${TICKERS[@]}"; do
  curl "https://allin.auincap.com/api/markdown/$ticker" \
    -o "reports/${ticker}_$(date +%Y%m%d).md"
done
```

### **場景 2：批量導出多個公司的特定分析**

```bash
# 導出所有公司的「商業模式分析」
for ticker in NVDA AAPL MSFT TSLA GOOG; do
  curl "https://allin.auincap.com/api/markdown/$ticker/biz?lang=en" \
    -o "business_models/${ticker}_biz.md"
done
```

### **場景 3：集成到內部系統**

```python
import requests
import os

def get_analysis_report(ticker: str, sections: list, lang: str = "zh_hk") -> str:
    """取得分析報告"""
    sections_str = ",".join(sections)
    url = f"https://allin.auincap.com/api/markdown/{ticker}"
    params = {
        "sections": sections_str,
        "lang": lang
    }

    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"API 請求失敗: HTTP {response.status_code}")

# 使用範例
try:
    report = get_analysis_report("NVDA", ["biz", "finance"], lang="en")
    with open("NVDA_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("✅ 報告已保存")
except Exception as e:
    print(f"❌ 錯誤: {e}")
```

---

## 🔍 錯誤處理

### **404 Not Found - 快取不存在**

```json
HTTP/1.1 404 Not Found
```

**原因**: 該 ticker/section 尚未生成快取

**解決方案**:
1. 訪問網頁 UI：`https://allin.auincap.com/{ticker}`
2. 點擊相應的分析卡片以觸發分析
3. 等待 AI 分析完成（通常 30-60 秒）
4. 重新請求 API

### **400 Bad Request - 無效參數**

```json
HTTP/1.1 400 Bad Request
```

**檢查清單**:
- [ ] ticker 格式是否正確（例如：0700.HK 不是 700.HK）
- [ ] section 名稱是否拼寫正確
- [ ] lang 參數是否為 zh_hk / zh_cn / en

### **503 Service Unavailable - 伺服器過載**

```json
HTTP/1.1 503 Service Unavailable
```

**處理方式**:
- 等待 30-60 秒後重試
- 使用指數退避重試機制

---

## 📊 性能指標

| 指標 | 值 |
|------|-----|
| 平均響應時間 | < 200 ms |
| 最大檔案大小 | ~ 50 MB（完整報告） |
| 同時連接數限制 | 無（目前） |
| 速率限制 | 無（目前） |

---

## 🔐 安全性說明

✅ **當前實現**:
- 無需 API Key（公開 API）
- 所有請求均使用 HTTPS（生產環境）
- Ticker 格式驗證（防止目錄遍歷）

⚠️ **生產環境建議**:
- 若需要增加 API Key 驗證，請聯絡開發團隊
- 監控 API 使用情況
- 根據需要實施速率限制

---

## 📦 集成指南

### **Python 3.8+**

```python
import requests

def download_analysis(ticker: str, section: str = None, lang: str = "zh_hk"):
    """下載分析報告"""

    if section:
        url = f"https://allin.auincap.com/api/markdown/{ticker}/{section}"
    else:
        url = f"https://allin.auincap.com/api/markdown/{ticker}"

    params = {"lang": lang}
    response = requests.get(url, params=params, timeout=10)

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"HTTP {response.status_code}")
```

### **Node.js / JavaScript**

```javascript
async function getAnalysis(ticker, section = null, lang = "zh_hk") {
  let url = `https://allin.auincap.com/api/markdown/${ticker}`;

  if (section) {
    url += `/${section}`;
  }

  url += `?lang=${lang}`;

  const response = await fetch(url);
  if (response.ok) {
    return await response.text();
  } else {
    throw new Error(`HTTP ${response.status}`);
  }
}

// 使用
getAnalysis("NVDA", "biz", "en")
  .then(content => console.log(content))
  .catch(err => console.error(err));
```

### **Bash / cURL**

```bash
# 下載單一 section
curl -H "Accept: text/markdown" \
  https://allin.auincap.com/api/markdown/NVDA/biz \
  -o report.md

# 下載合併報告
curl "https://allin.auincap.com/api/markdown/NVDA?sections=biz,finance,exec" \
  -o full_report.md
```

---

## 📞 技術支援

| 項目 | 聯絡資訊 |
|------|----------|
| 報告 Bug | aaron@auincap.com |
| 功能請求 | aaron@auincap.com |
| 文檔更新 | 此文檔同步至 GitHub |

---

## 📝 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.0 | 2026-03-11 | 初始發佈 |

---

## ✅ 檢查清單（部署前）

- [ ] API 端點在生產環境可訪問
- [ ] 至少有 3 個 ticker 的快取已生成
- [ ] HTTPS 已啟用
- [ ] 防火牆規則允許 API 訪問
- [ ] 監控和日誌記錄已配置
- [ ] IT 部門已測試 API 連接

---

**此文檔版本**: 2026-03-11
**最後更新**: 2026-03-11
