# 蟲蟲報告 - Aurum-Infinity-AI

## 關鍵問題

### 1. **`analyze_section()` 中缺少 `exchange` 變數** ⚠️ 高度優先
**位置:** [app.py:287-293](app.py#L287-L293)

**問題:**
當 `analyze_section()` 呼叫 `get_stock_info()` 時，它提取 `stock_name` 和 `exchange`。但是，如果股票已經在快取中，程式碼邏輯可能有問題。

```python
stock_name, exchange = get_stock_info(ticker)  # 第 287 行
if stock_name is None:
    return jsonify({"success": False, "error": f"找不到 {ticker} 的資料"})

chinese_name = stock_name
if not get_stock(ticker):  # 如果股票已存在於快取...
    save_stock(ticker, stock_name, chinese_name, exchange)
```

**實際狀況:** ✅ **假警報** - 程式碼是安全的。`exchange` 變數在第 287 行一定會設定，因為 `get_stock_info()` 總是被執行。即使快取已有股票，`exchange` 仍然可用於第 300 行的 `prompt_manager.build()`。

---

### 2. **純文本儲存管理員密碼** ⚠️ 中度優先
**位置:** [admin_auth.py:40-42](admin_auth.py#L40-L42)

**問題:**
管理員密碼以純文本形式儲存在 `.env` 中，直接比較：

```python
def verify_admin_password(password: str) -> bool:
    """驗證輸入的密碼是否正確"""
    return password == _get_admin_password()
```

**影響:**
- 如果 `.env` 檔案暴露（git commit、伺服器備份），管理員密碼被破解
- 無密碼複雜性要求
- 無密碼加密或 hash 保護

**建議修復:**
使用 bcrypt 或 argon2 對密碼進行 hash 儲存和驗證。

```python
import hashlib

def verify_admin_password(password: str) -> bool:
    stored_hash = os.getenv('ADMIN_PASSWORD_HASH', '')
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash
```

**暫時緩解:** 確保 `.env` 在 `.gitignore` 中（✅ 已完成），並設置文件權限 `chmod 600 .env`。

---

### 3. **YAML 檔案更新中的競爭條件** ⚠️ 低度優先
**位置:** [prompt_manager.py:154-170](prompt_manager.py#L154-L170)

**問題:**
如果兩個管理員請求同時執行 `update_section_prompt()`，可能會發生檔案寫入衝突：

```python
def update_section_prompt(self, section: str, new_prompt: str):
    self._reload_if_changed()  # 載入當前檔案
    self._config['sections'][section]['prompt'] = new_prompt  # 在記憶體中修改

    with open(self.yaml_path, 'w', encoding='utf-8') as f:  # 寫回檔案
        yaml.dump(self._config, f, ...)  # ← 競爭條件在這裡
```

**影響:**
- 最後寫入的值會覆蓋之前的值
- 如果兩個管理員同時編輯不同的區塊，其中一個可能被覆蓋

**建議修復:**
使用臨時檔案 + 原子性重命名：

```python
import tempfile
import os

def update_section_prompt(self, section: str, new_prompt: str):
    self._reload_if_changed()

    # 先寫到臨時檔案
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(self.yaml_path), text=True)
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            self._config['sections'][section]['prompt'] = new_prompt
            yaml.dump(self._config, f, ...)

        # 原子性重命名
        os.replace(tmp_path, self.yaml_path)
        self._last_modified = os.path.getmtime(self.yaml_path)
    except:
        os.unlink(tmp_path)
        raise
```

---

### 4. **缺少 `exchange` 鍵值驗證** ⚠️ 低度優先
**位置:** [read_stock_code.py:51-56](read_stock_code.py#L51-L56)

**問題:**
`get_stock_info()` 可能在股票資料格式錯誤時拋出 `KeyError`：

```python
def get_stock_info(ticker: str) -> tuple[str, str] | tuple[None, None]:
    _, entry = _find(ticker)
    if entry:
        return entry["name"], entry["exchange"]  # 如果缺少 "exchange" 鍵會拋出 KeyError
    return None, None
```

**影響:**
- API 返回 500 伺服器錯誤而不是 400 錯誤
- 前端無法優雅處理

**建議修復:**
```python
def get_stock_info(ticker: str) -> tuple[str, str] | tuple[None, None]:
    _, entry = _find(ticker)
    if entry and "name" in entry and "exchange" in entry:
        return entry["name"], entry["exchange"]
    return None, None
```

---

### 5. **Markdown HTML 注入風險** ⚠️ 低度優先
**位置:** [app.py:307-310](app.py#L307-L310)

**問題:**
Gemini API 的回應直接轉換為 HTML，但 markdown 允許原始 HTML：

```python
response_text = call_gemini_api(prompt, use_search=True)
html_content = markdown.markdown(
    response_text,
    extensions=['tables', 'fenced_code', 'nl2br']
)
# 如果 response_text 包含 <script>alert('XSS')</script>，它會被直接渲染
```

**影響:**
- 低風險 - Gemini 是信任的第三方
- 但如果 API 被破解或資料被修改，XSS 攻擊成為可能

**建議修復:**
使用 `bleach` 庫清理 HTML：

```python
import bleach

html_content = markdown.markdown(
    response_text,
    extensions=['tables', 'fenced_code', 'nl2br']
)

# 清理只允許特定標籤
clean_html = bleach.clean(
    html_content,
    tags=['p', 'h1', 'h2', 'h3', 'h4', 'table', 'tr', 'td', 'th', 'code', 'pre', 'ul', 'ol', 'li', 'strong', 'em', 'br', 'blockquote', 'hr'],
    strip=True
)
save_section_html(ticker, section, clean_html)
```

---

### 6. **Admin 路由保護驗證** ✅ 假警報
**位置:** [app.py:419-457](app.py#L419-L457)

路由 `/admin/resolve_vars` 和 `/admin/prompts/<section_key>/preview` 都有 `@admin_required` 裝飾器保護。

**狀況:** ✅ 沒有問題 - 所有管理員路由都受保護。

---

### 7. **XSS 防護 - Jinja2 自動轉義** ✅ 假警報
**位置:** [templates/admin/prompt_editor.html](templates/admin/prompt_editor.html)

Jinja2 的 `{{ }}` 語法預設會自動轉義 HTML 字符。

**狀況:** ✅ 沒有 XSS 漏洞 - 框架已保護。

---

## 問題總結表

| # | 問題 | 嚴重程度 | 狀況 | 建議 |
|---|------|--------|------|------|
| 1 | 缺少 exchange 變數 | 高 | ✅ 假警報 | 無須修復 |
| 2 | 純文本儲存密碼 | **中** | ⚠️ 需修復 | **使用 bcrypt/argon2** |
| 3 | YAML 檔案競爭條件 | 低 | ⚠️ 需修復 | **原子性寫入** |
| 4 | 缺少 exchange 鍵驗證 | 低 | ⚠️ 需修復 | **驗證鍵值存在** |
| 5 | Markdown HTML 注入 | 低 | ⚠️ 需修復 | **使用 bleach 清理** |
| 6 | Admin 路由保護 | 中 | ✅ 假警報 | 無須修復 |
| 7 | XSS 防護 | 中 | ✅ 假警報 | 無須修復 |

---

## 優先級建議

### 必須修復（安全性）
- [ ] **問題 #2:** 使用 bcrypt 或 argon2 對管理員密碼進行 hash
- [ ] **問題 #5:** 使用 bleach 庫清理 Markdown HTML 輸出

### 應該修復（資料完整性）
- [ ] **問題 #3:** 使用臨時檔案 + 原子性重命名防止 YAML 寫入衝突
- [ ] **問題 #4:** 驗證股票資料中 `exchange` 鍵值存在

### 可選改進
- 無

---

## 測試命令

```bash
# 測試 ticker 驗證
curl http://localhost:5000/../../../etc/passwd       # 應返回 404
curl http://localhost:5000/.env                      # 應返回 404
curl "http://localhost:5000/<script>alert(1)</script>" # 應返回 404

# 測試無效 ticker
curl -X POST http://localhost:5000/analyze/biz \
  -H "Content-Type: application/json" \
  -d '{"ticker":"INVALID_VERY_LONG_TICKER_9999999"}'

# 測試管理員登入
curl -X POST http://localhost:5000/admin/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "password=test123"
```

---

## 程式碼品質評估

**整體評分: 8.5/10** ✅ 生產就緒

**優點:**
- ✅ 強大的 Ticker 驗證（3 層防護）
- ✅ 清晰的檔案結構與模組化設計
- ✅ 完整的快取管理系統
- ✅ 完善的日誌系統
- ✅ 響應式前端設計
- ✅ Jinja2 自動轉義 XSS 防護

**缺點:**
- ❌ 純文本密碼儲存（安全風險）
- ⚠️ YAML 寫入缺少並發控制
- ⚠️ Markdown HTML 未清理（低風險）
- ⚠️ 股票資料驗證不完整

**建議:** 先修復問題 #2（密碼安全）和 #5（HTML 清理），其他問題可在下一個開發週期解決。

