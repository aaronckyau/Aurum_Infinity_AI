#!/usr/bin/env python3
"""
REST API Markdown 測試腳本
測試 /api/markdown/<ticker> 和 /api/markdown/<ticker>/<section> 端點
"""

import requests
import os
import sys
from pathlib import Path

# ============================================================================
# 設定
# ============================================================================

API_BASE = "http://localhost:5000"
TEST_TICKER = "NVDA"
TEST_SECTIONS = ["biz", "finance", "exec"]
OUTPUT_DIR = Path("test_output")

# 顏色輸出
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


# ============================================================================
# 工具函數
# ============================================================================

def log_success(msg: str):
    """綠色成功日誌"""
    print(f"{GREEN}✅ {msg}{RESET}")


def log_error(msg: str):
    """紅色錯誤日誌"""
    print(f"{RED}❌ {msg}{RESET}")


def log_info(msg: str):
    """資訊日誌"""
    print(f"{BOLD}ℹ️  {msg}{RESET}")


def log_warning(msg: str):
    """黃色警告日誌"""
    print(f"{YELLOW}⚠️  {msg}{RESET}")


# ============================================================================
# 測試函數
# ============================================================================

def test_single_section(ticker: str, section: str, lang: str = "zh_hk") -> bool:
    """
    測試單一 section API
    GET /api/markdown/<ticker>/<section>?lang=...
    """
    url = f"{API_BASE}/api/markdown/{ticker}/{section}?lang={lang}"
    filename = f"{ticker}_{section}_{lang}.md"
    filepath = OUTPUT_DIR / filename

    log_info(f"測試: GET {url}")

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            # 保存檔案
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)

            # 驗證內容
            if len(response.text) > 100 and "#" in response.text:
                log_success(f"取得 {ticker}/{section} → {filepath} ({len(response.text)} bytes)")
                return True
            else:
                log_error(f"檔案內容無效: {filename}")
                return False
        elif response.status_code == 404:
            log_warning(f"未找到快取: {ticker}/{section} (可能需要先觸發分析)")
            return False
        else:
            log_error(f"HTTP {response.status_code}: {response.text[:100]}")
            return False

    except requests.exceptions.ConnectionError:
        log_error(f"無法連接到 {API_BASE}，請確認伺服器已啟動")
        return False
    except Exception as e:
        log_error(f"請求失敗: {e}")
        return False


def test_combined_sections(ticker: str, sections: list, lang: str = "zh_hk") -> bool:
    """
    測試合併多個 sections API
    GET /api/markdown/<ticker>?sections=biz,finance,exec&lang=...
    """
    sections_str = ",".join(sections)
    url = f"{API_BASE}/api/markdown/{ticker}?sections={sections_str}&lang={lang}"
    filename = f"{ticker}_combined_{lang}.md"
    filepath = OUTPUT_DIR / filename

    log_info(f"測試: GET {url}")

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            # 保存檔案
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)

            # 驗證內容
            section_count = sum(1 for s in sections if f"## " in response.text)
            if len(response.text) > 200:
                log_success(f"取得合併報告 → {filepath} ({len(response.text)} bytes, {sections_str})")
                return True
            else:
                log_error(f"檔案內容無效: {filename}")
                return False

        elif response.status_code == 404:
            log_warning(f"未找到快取: {ticker} 的任何 section")
            return False
        else:
            log_error(f"HTTP {response.status_code}: {response.text[:100]}")
            return False

    except requests.exceptions.ConnectionError:
        log_error(f"無法連接到 {API_BASE}，請確認伺服器已啟動")
        return False
    except Exception as e:
        log_error(f"請求失敗: {e}")
        return False


def test_all_sections(ticker: str, lang: str = "zh_hk") -> bool:
    """
    測試獲取所有 sections（不指定 sections 參數）
    GET /api/markdown/<ticker>?lang=...
    """
    url = f"{API_BASE}/api/markdown/{ticker}?lang={lang}"
    filename = f"{ticker}_full_{lang}.md"
    filepath = OUTPUT_DIR / filename

    log_info(f"測試: GET {url}")

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            # 保存檔案
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)

            if len(response.text) > 200:
                log_success(f"取得全部分析 → {filepath} ({len(response.text)} bytes)")
                return True
            else:
                log_error(f"檔案內容無效: {filename}")
                return False

        elif response.status_code == 404:
            log_warning(f"未找到快取: {ticker}")
            return False
        else:
            log_error(f"HTTP {response.status_code}: {response.text[:100]}")
            return False

    except requests.exceptions.ConnectionError:
        log_error(f"無法連接到 {API_BASE}，請確認伺服器已啟動")
        return False
    except Exception as e:
        log_error(f"請求失敗: {e}")
        return False


def test_different_languages(ticker: str, section: str) -> bool:
    """測試不同語言的 API"""
    languages = ["zh_hk", "zh_cn", "en"]
    results = []

    for lang in languages:
        url = f"{API_BASE}/api/markdown/{ticker}/{section}?lang={lang}"
        log_info(f"測試: {lang} → GET {url}")

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                log_success(f"✓ {lang} 版本可用")
                results.append(True)
            elif response.status_code == 404:
                log_warning(f"✗ {lang} 版本未快取")
                results.append(False)
            else:
                log_error(f"✗ {lang} HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            log_error(f"✗ {lang} 請求失敗: {e}")
            results.append(False)

    return any(results)


# ============================================================================
# 主測試
# ============================================================================

def main():
    print(f"\n{BOLD}{'='*70}")
    print(f"REST API Markdown 測試")
    print(f"{'='*70}{RESET}\n")

    # 創建輸出目錄
    OUTPUT_DIR.mkdir(exist_ok=True)
    log_info(f"輸出目錄: {OUTPUT_DIR.absolute()}\n")

    test_results = []

    # ── 測試 1: 單一 Section ──────────────────────────────────────
    print(f"\n{BOLD}測試 1: 單一 Section{RESET}")
    print("-" * 70)
    for section in TEST_SECTIONS[:1]:  # 測試第一個 section
        result = test_single_section(TEST_TICKER, section)
        test_results.append(("single_section", result))

    # ── 測試 2: 合併多個 Sections ────────────────────────────────
    print(f"\n{BOLD}測試 2: 合併多個 Sections{RESET}")
    print("-" * 70)
    result = test_combined_sections(TEST_TICKER, TEST_SECTIONS[:2])
    test_results.append(("combined_sections", result))

    # ── 測試 3: 獲取全部分析 ──────────────────────────────────────
    print(f"\n{BOLD}測試 3: 獲取全部分析{RESET}")
    print("-" * 70)
    result = test_all_sections(TEST_TICKER)
    test_results.append(("all_sections", result))

    # ── 測試 4: 不同語言版本 ──────────────────────────────────────
    print(f"\n{BOLD}測試 4: 不同語言版本{RESET}")
    print("-" * 70)
    result = test_different_languages(TEST_TICKER, TEST_SECTIONS[0])
    test_results.append(("multi_language", result))

    # ── 測試摘要 ──────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*70}")
    print(f"測試摘要")
    print(f"{'='*70}{RESET}")

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status} - {test_name}")

    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        log_success("所有測試通過！")
        print(f"\n📁 下載的檔案位於: {OUTPUT_DIR.absolute()}\n")
        return 0
    else:
        log_warning(f"有 {total - passed} 個測試失敗")
        print(f"\n💡 提示: 如果快取不存在，請先訪問網頁 UI 觸發分析\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
