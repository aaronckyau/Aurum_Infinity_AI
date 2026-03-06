# Pre-Deploy Code Review Report
**Date:** 2026-03-06
**Files Reviewed:** terminal.js, terminal.css, index.html

---

## 1. BUGS

### [BUG-01] `window-body` padding 重複定義 — CSS
**檔案:** `terminal.css`
**位置:** 第 423 行 & 第 501 行（同在 `@media (max-width: 640px)` 內）
**問題:** `.window-body` 在同一個 media query 裡出現兩次，第二個會覆蓋第一個，但第一個的 `position: relative` 備註會讓人誤以為 sticky header 依賴它。
```css
/* 第 423 行 */
.window-body { padding: 20px 16px; position: relative; }

/* 第 501 行（覆蓋上面） */
.window-body { padding: 20px 16px 40px 16px; }
```
**修復建議:** 合併為一個規則，移除第 423 行的 `.window-body`。

---

### [BUG-02] Swipe-down 手勢與內容滾動衝突
**檔案:** `terminal.js`
**位置:** 第 286–317 行
**問題:** `touchmove` 在 `window-body` 滾動時也會觸發，導致用戶向下滾動閱讀時可能意外觸發關閉（opacity 漸褪）。`touchstart` 監聽在整個 `win` 上，沒有判斷是否從 header 區域開始滑動。
**修復建議:** 限制 swipe 偵測只在 `windowHeader` 上觸發，或加入「scrollTop === 0 才允許 swipe 關閉」的判斷。

---

### [BUG-03] `window-header` sticky 只在手機 640px 才啟用，但 `window-body` overflow 在桌面也需要
**檔案:** `terminal.css`
**位置:** 第 440–444 行
**問題:** Sticky header 只在手機設定，但 `.draggable-window` 用 `overflow: hidden`，桌面 sticky 不生效（雖然不需要，但邏輯容易混淆）。
**影響:** 低，但需留意。

---

## 2. 功能問題

### [FUNC-01] `btn-{id}` 元素已不存在，但 JS 仍在操作它
**檔案:** `terminal.js`
**位置:** 第 66、108、457 行
**問題:** HTML 中已移除 `id="btn-{id}"` 的「開啟報告」按鈕，但 JS 的 `fetchSection()` 和 `navigateToStock()` 仍嘗試操作它。
```javascript
const btn = document.getElementById(`btn-${sectionId}`);  // 永遠是 null
if (btn) btn.classList.remove('hidden');  // 永遠不執行
```
**影響:** 不會 crash（有 null 判斷），但屬於死代碼（dead code）。

---

### [FUNC-02] `badge-{id}` 元素不存在
**檔案:** `terminal.js`
**位置:** 第 68、79、111–115 行
**問題:** `fetchSection()` 嘗試取得 `badge-{id}` 元素，但 HTML 中完全沒有這個 ID。快取標記（非即時數據 / AI 即時分析）永遠不會顯示。
**影響:** 功能靜默失效，用戶看不到資料來源標記。

---

### [FUNC-03] `updateSection()` 有 confirm 對話框但按鈕已隱藏
**檔案:** `terminal.js`
**位置:** 第 137–149 行
**問題:** 函數仍存在並可被呼叫，但 HTML 中按鈕已隱藏。若未來重新啟用，`confirm()` 在手機 iOS 部分瀏覽器可能被 block。
**影響:** 現在無影響，但留意未來重啟時。

---

### [FUNC-04] `navigator.clipboard` 在 HTTP（非 HTTPS）環境不可用
**檔案:** `terminal.js`
**位置:** 第 267、272 行
**問題:** 分享功能的 fallback 使用 `navigator.clipboard.writeText()`，在非 HTTPS 環境（如 production HTTP）會拋出 undefined error，且沒有 try/catch 保護。
```javascript
navigator.clipboard.writeText(...)  // HTTP 環境下 clipboard 為 undefined
```
**修復建議:** 加上 try/catch 或先判斷 `navigator.clipboard` 是否存在。

---

## 3. 無用代碼（Dead Code）

### [DEAD-01] `update-btn` CSS 樣式（舊按鈕）
**檔案:** `terminal.css`
**位置:** 第 57–60 行
```css
.update-btn { display: none !important; }
```
**說明:** 舊的「重新分析」按鈕樣式，HTML 已改用 `update-btn-small` 且設為 `display: none !important`。`.update-btn` 這個 class 在 HTML 中已無任何元素使用。可安全刪除。

---

### [DEAD-02] `update-btn-small` CSS 樣式
**檔案:** `terminal.css`
**位置:** 第 62–75 行
**說明:** 按鈕已在 HTML 強制 `style="display: none !important"` 隱藏，這些 CSS 不會被用到。可安全刪除（或保留供日後重啟使用）。

---

### [DEAD-03] JS 文件頭部 ID 規則說明已過時
**檔案:** `terminal.js`
**位置:** 第 8–9 行
```javascript
// DOM 元素 ID 規則：dot-{id}, preview-{id}, btn-{id}, update-{id}, badge-{id}
```
**說明:** `btn-{id}` 和 `badge-{id}` 已不存在，說明文件應更新。

---

### [DEAD-04] `SVG_PROGRESS_BAR_GUIDE.md`
**檔案:** 根目錄
**說明:** 進度條已從 SVG 改為 CSS div，此指南文件內容已過時，但不影響生產環境（純文件）。

---

## 4. 總結

| 類別 | 數量 | 嚴重程度 |
|------|------|---------|
| Bug（需修復） | 3 | BUG-02 中等，其餘低 |
| 功能問題 | 4 | FUNC-04 需上線前修復 |
| 死代碼 | 4 | 低（不影響功能） |

### 上線前必須修復：
- **FUNC-04** — `navigator.clipboard` 加 try/catch，防止 HTTP 環境 crash

### 建議修復（不阻礙上線）：
- **BUG-01** — 合併重複的 `.window-body` CSS
- **BUG-02** — Swipe 手勢加入 scrollTop 判斷
- **FUNC-01、FUNC-02** — 移除 `btn` 和 `badge` 的死代碼

### 可之後清理：
- **DEAD-01 至 DEAD-04** — 清除無用樣式和過時文件
