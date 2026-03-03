"""
Stock Analyzer - 主程式（Google Gemini 3 Flash 版本 + 靜態 HTML 快取）
============================================================================
API：Google Gemini API + Google Search Grounding（自帶網絡搜索）
  - 模型：gemini-3-flash-preview
  - SDK：google-genai
  - 快取：靜態 HTML 檔案（cache/{TICKER}/ 資料夾）

URL 結構：
  /          → 跳轉到預設標的（NVDA）
  /AAPL      → 蘋果股票分析頁
  /0700.HK   → 騰訊股票分析頁（輸入 700 也會跳轉到這裡）
  /601899.SS → A 股分析頁
============================================================================
"""
from dotenv import load_dotenv
import os
import time
from datetime import datetime

import markdown
from flask import Flask, render_template, request, jsonify, redirect

from google import genai
from google.genai import types

from prompt_manager import PromptManager
from file_cache import (
    get_stock, get_section_html, save_stock, save_section_html, VALID_SECTIONS
)
from read_stock_code import normalize_ticker, get_canonical_ticker, get_stock_info, search_stocks

# ============================================================================
# Configuration
# ============================================================================
load_dotenv()


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-3-flash-preview"
    DEFAULT_TICKER = 'NVDA'
    PROMPTS_PATH = os.path.join(os.path.dirname(__file__), 'prompts', 'prompts.yaml')
    API_MAX_TOKENS = 8000
    API_MAX_RETRIES = 2
    API_RETRY_DELAY = 5


app = Flask(__name__)


def get_today() -> str:
    return datetime.now().strftime('%Y/%m/%d')


# ============================================================================
# 初始化 Gemini Client 與 PromptManager
# ============================================================================
gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
prompt_manager = PromptManager(Config.PROMPTS_PATH)


# ============================================================================
# 工具函數
# ============================================================================

def resolve_ticker(raw: str) -> str:
    """
    將用戶輸入的任意格式代碼，解析成官方代碼（canonical ticker）。

    邏輯：
      1. 先用 normalize_ticker 做基本格式化（例如 1398 → 1398.HK）
      2. 再用 get_canonical_ticker 查 JSON 資料庫取得官方代碼
         （例如 1398.HK → 01398.HK）
      3. 如果 JSON 找不到（美股等），保留 normalize_ticker 的結果

    比喻：就像查電話簿，不管你怎麼寫名字，最終都會找到同一個正式登記名稱。
    """
    normalized = normalize_ticker(raw)
    canonical = get_canonical_ticker(normalized) or get_canonical_ticker(raw)
    return canonical if canonical else normalized


# ============================================================================
# Gemini API Functions
# ============================================================================

def call_gemini_api(prompt: str, use_search: bool = True) -> str:
    """調用 Gemini API，支援聯網搜索"""
    config_params = {
        "temperature": 0.7,
        "max_output_tokens": Config.API_MAX_TOKENS,
    }

    if use_search:
        config_params["tools"] = [
            types.Tool(google_search=types.GoogleSearch())
        ]

    config = types.GenerateContentConfig(**config_params)

    for attempt in range(Config.API_MAX_RETRIES + 1):
        try:
            response = gemini_client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            if response.text:
                return response.text
            else:
                return "⚠️ API 回覆為空或被安全過濾。"

        except Exception as e:
            print(f"[Gemini] Error (attempt {attempt + 1}): {e}")
            if attempt < Config.API_MAX_RETRIES:
                time.sleep(Config.API_RETRY_DELAY)
                continue
            return f"⚠️ API 錯誤: {str(e)}"

    return "⚠️ API 請求失敗。"


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def home():
    """根路徑：跳轉到預設標的"""
    return redirect(f'/{Config.DEFAULT_TICKER}')


@app.route('/<ticker_raw>')
def index(ticker_raw: str):
    """
    股票分析主頁
    URL 範例：/AAPL、/700、/1398、/0700.HK

    流程：
      1. 解析成官方代碼（canonical ticker）
      2. 若 URL 不是官方代碼，做 301 跳轉（確保唯一 URL）
      3. 讀取靜態 HTML 快取
      4. 快取不存在 → 從 JSON 查詢名稱並儲存
    """
    # 忽略瀏覽器自動請求的系統路徑
    if ticker_raw.lower() in ('favicon.ico', 'robots.txt', 'sitemap.xml'):
        return '', 404

    # ★ 解析成官方代碼（核心修復）
    ticker = resolve_ticker(ticker_raw)

    # ★ 若 URL 不是官方代碼，做 301 跳轉
    # 例如用戶訪問 /1398 → 跳轉到 /01398.HK
    if ticker != ticker_raw.upper():
        return redirect(f'/{ticker}', code=301)

    # ★ 讀取靜態快取（info.json）
    stock_info = get_stock(ticker)

    if stock_info:
        print(f"[Cache] 從快取讀取基本資料 {ticker}")
        stock_name = stock_info['stock_name']
        chinese_name = stock_info['chinese_name']
    else:
        # 快取不存在 → 從本地 JSON 查詢名稱
        stock_name, exchange = get_stock_info(ticker)

        if stock_name is None:
            return render_template('error.html', ticker=ticker_raw, date=get_today()), 404

        chinese_name = stock_name

        # ★ 儲存基本資料到 cache/{TICKER}/info.json
        save_stock(
            ticker=ticker,
            stock_name=stock_name,
            chinese_name=chinese_name,
            exchange=exchange,
        )
        print(f"[Cache] 儲存新股票基本資料 {ticker} → cache/")

    # ★ 讀取各分析區塊的靜態 HTML 快取
    cached_sections_html = {}
    for section_key in VALID_SECTIONS:
        html = get_section_html(ticker, section_key)
        if html:
            cached_sections_html[section_key] = html

    return render_template(
        'index.html',
        ticker=ticker,
        stock_name=stock_name,
        chinese_name=chinese_name,
        m={"eps": "-", "pe": "-", "yield": "-", "short": "-", "cap": "-", "vol": "-"},
        date=get_today(),
        sections=prompt_manager.get_section_names(),
        cached_sections=cached_sections_html if cached_sections_html else None
    )


@app.route('/api/search_stock')
def search_stock():
    """股票代碼自動完成 API"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 1:
        return jsonify([])
    results = search_stocks(query, limit=8)
    return jsonify(results)


@app.route('/analyze/<section>', methods=['POST'])
def analyze_section(section: str):
    if section not in VALID_SECTIONS:
        return jsonify({"success": False, "error": "非法的分析類別"}), 400

    raw_ticker = request.json.get('ticker', '')

    # ★ 核心修復：統一解析成官方代碼，確保快取一致
    ticker = resolve_ticker(raw_ticker)

    force_update = request.json.get('force_update', False)

    # ★ 非強制更新時，先讀取靜態 HTML 快取
    if not force_update:
        cached_html = get_section_html(ticker, section)
        if cached_html:
            print(f"[Cache] 從快取讀取 {ticker} - {section}")
            return jsonify({
                "success": True,
                "report": cached_html,
                "from_cache": True
            })

    # ★ 需要呼叫 AI（首次查詢或強制更新）
    stock_name, exchange = get_stock_info(ticker)

    if stock_name is None:
        return jsonify({"success": False, "error": f"找不到 {ticker} 的資料"})

    chinese_name = stock_name

    # 確保基本資料快取存在（首次時補存）
    if not get_stock(ticker):
        save_stock(ticker, stock_name, chinese_name, exchange)

    try:
        prompt = prompt_manager.build(
            section=section,
            ticker=ticker,
            stock_name=stock_name,
            exchange=exchange,
            today=get_today(),
            chinese_name=chinese_name,
        )

        print(f"[AI] 呼叫 Gemini AI 分析 {ticker} - {section}")
        response_text = call_gemini_api(prompt, use_search=True)

        # ★ 轉換為 HTML 後直接儲存成靜態 HTML 檔案
        html_content = markdown.markdown(
            response_text,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        save_section_html(ticker, section, html_content)
        print(f"[Cache] 已儲存 {ticker} - {section} → cache/{ticker}/{section}.html")

        return jsonify({
            "success": True,
            "report": html_content,
            "from_cache": False
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
