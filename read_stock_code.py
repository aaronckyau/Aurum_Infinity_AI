import json
import os
import glob

# JSON files live in the stock_code/ subfolder alongside this script
_STOCK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_code")

def _load_lookup() -> dict:
    files = sorted(glob.glob(os.path.join(_STOCK_DIR, "stock_code_*.json")))
    path = files[-1] if files else os.path.join(_STOCK_DIR, "stock_code.json")
    with open(path, encoding="utf-8") as f:
        print(f"[stock_lookup] Loaded: {os.path.basename(path)}")
        return json.load(f)

_lookup = _load_lookup()


def normalize_ticker(ticker: str) -> str:
    raw = ticker.upper().strip()
    if '.' in raw or not raw.isdigit():
        return raw
    return raw.zfill(4) + '.HK' if len(raw) <= 4 else raw


def _find(ticker: str) -> dict | None:
    """Return the raw JSON entry for a ticker, or None."""
    code = normalize_ticker(ticker)
    base = code.split('.')[0]
    for key in [code, base] + [base.zfill(n) for n in (4, 5, 6)]:
        if key in _lookup:
            return _lookup[key]
    return None


def get_stock_info(ticker: str) -> tuple[str, str] | tuple[None, None]:
    """Return (name, exchange) for use by app.py, or (None, None) if not found."""
    entry = _find(ticker)
    if entry:
        return entry["name"], entry["exchange"]
    return None, None


def get_name(ticker: str) -> str:
    """Return formatted name + exchange for CLI display."""
    entry = _find(ticker)
    if entry:
        return f"{entry['name']}  [{entry['exchange']}]"
    return f"Not found: {ticker}"


def _exchange_priority(exchange: str) -> int:
    """
    排序優先級（數字越小越前）：
      HK = 0（最優先）
      US exchanges = 1
      其他（CN 等）= 2
    """
    ex = exchange.upper()
    if ex in ('HK', 'HKEX'):
        return 0
    if ex in ('NYSE', 'NASDAQ', 'AMEX', 'US'):
        return 1
    return 2


def search_stocks(query: str, limit: int = 8) -> list[dict]:
    """
    搜尋股票代碼或名稱，回傳最多 limit 筆結果。

    排序邏輯（純數字輸入時）：
      1. HK 股優先（exchange = HK）
      2. 代碼長度短的優先（00388 比 000388 短）
      3. 代碼字母順序

    非純數字輸入（英文）：
      1. 代碼前綴完全匹配優先
      2. 名稱包含關鍵字補充
    """
    q_upper = query.upper().strip()
    q_lower = query.lower().strip()
    is_numeric = q_upper.isdigit()

    matches = []
    seen = set()

    for code, entry in _lookup.items():
        if code in seen:
            continue

        matched = False

        if is_numeric:
            # 純數字：取代碼的數字部分來比對前綴
            # 例如輸入 "388"，代碼 "00388" 的數字部分是 "00388"
            # 去掉前綴零後比對，或直接用 startswith
            numeric_part = code.split('.')[0]  # "00388" or "000388"
            # 同時支援：帶前導零 "00388" 或去零 "388" 都能匹配
            if numeric_part.startswith(q_upper) or numeric_part.lstrip('0').startswith(q_upper.lstrip('0') or '0'):
                matched = True
        else:
            # 英文/混合：代碼前綴 或 名稱包含
            if code.startswith(q_upper) or q_lower in entry["name"].lower():
                matched = True

        if matched:
            matches.append({
                "code": code,
                "name": entry["name"],
                "exchange": entry["exchange"],
            })
            seen.add(code)

    # ── 排序 ──────────────────────────────────────────────
    if is_numeric:
        # 純數字輸入：HK 優先 → 代碼長度短優先 → 代碼字母順序
        matches.sort(key=lambda x: (
            _exchange_priority(x["exchange"]),  # 0=HK, 1=US, 2=CN...
            len(x["code"]),                     # 代碼長度（短的優先）
            x["code"],                          # 字母順序
        ))
    else:
        # 英文輸入：代碼完全前綴 → 交易所優先 → 字母順序
        matches.sort(key=lambda x: (
            0 if x["code"].startswith(q_upper) else 1,
            _exchange_priority(x["exchange"]),
            x["code"],
        ))

    return matches[:limit]


if __name__ == "__main__":
    print(f"Loaded {len(_lookup):,} entries from {_STOCK_DIR}")
    print("Type 'q' to quit.\n")
    while True:
        code = input("Stock code: ").strip()
        if code.lower() in ("q", "quit", "exit"):
            break
        if code:
            print(f"  → {get_name(code)}\n")
