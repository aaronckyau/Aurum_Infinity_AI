"""
Stock Analyzer - 主程式（gemini-3.1-flash-lite-preview 版本 + 靜態 HTML 快取）
============================================================================
API：Google Gemini API + Google Search Grounding（自帶網絡搜索）
  - SDK：google-genai
  - 快取：靜態 HTML 檔案（cache/{TICKER}/ 資料夾）

URL 結構：
  /          → 跳轉到預設標的（NVDA）
  /AAPL      → 蘋果股票分析頁
  /0700.HK   → 騰訊股票分析頁
  /601899.SS → A 股分析頁

安全防護：
  - is_valid_ticker() 白名單格式驗證
  - 非法請求直接 abort(404)，不渲染任何頁面
  - 防止惡意掃描（.env、POM.XML、MAIN.CFM 等）污染快取
============================================================================
"""
from dotenv import load_dotenv
import os
import re
import time
from datetime import datetime

import markdown
from flask import Flask, render_template, request, jsonify, redirect, abort, make_response

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
    GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL    = "gemini-3.1-flash-lite-preview"
    DEFAULT_TICKER  = 'NVDA'
    PROMPTS_PATH    = os.path.join(os.path.dirname(__file__), 'prompts', 'prompts.yaml')
    API_MAX_TOKENS  = 8000
    API_MAX_RETRIES = 2
    API_RETRY_DELAY = 5


app = Flask(__name__)


def get_today() -> str:
    return datetime.now().strftime('%Y/%m/%d')


# ============================================================================
# 初始化 Gemini Client 與 PromptManager
# ============================================================================
gemini_client  = genai.Client(api_key=Config.GEMINI_API_KEY)
prompt_manager = PromptManager(Config.PROMPTS_PATH)


# ============================================================================
# 安全防護：Ticker 格式白名單驗證
# ============================================================================

# 合法 ticker 正規表達式白名單：
#   美股／ETF  : 1–5 個英文字母           例如 AAPL、NVDA
#   美股含後綴  : 字母 + 點 + 字母         例如 BRK.B
#   港股       : 1–5 位數字 + .HK         例如 0700.HK
#   A 股       : 6 位數字 + .SS 或 .SZ    例如 601899.SS
#   其他市場   : 字母數字 + 點 + 2–3後綴   例如 005930.KS
#
# 比喻：就像門口保安只讓「有效員工證」的人進入，
#       .env、POM.XML、MAIN.CFM 等一律擋在門外，不解釋不回應。

_TICKER_PATTERN = re.compile(
    r'^(?:'
    r'[A-Z]{1,5}'                   # 純英文美股：AAPL、NVDA
    r'|[A-Z]{1,4}\.[A-Z]{1,2}'     # 英文含後綴：BRK.B
    r'|\d{1,6}\.[A-Z]{2,3}'        # 數字代碼（帶後綴）：0700.HK、601899.SS
    r'|\d{1,6}'                     # 純數字代碼（無後綴）：605196、00139、700
    r')$',
    re.IGNORECASE
)

# 靜態資源黑名單（優先攔截，直接 404）
_STATIC_BLACKLIST = frozenset([
    'favicon.ico', 'robots.txt', 'sitemap.xml',
    'apple-touch-icon.png', 'manifest.json',
])


def is_valid_ticker(raw: str) -> bool:
    """
    驗證輸入是否為合法股票代碼格式。

    防護目標：
      - .env、.env.backup              → 含點開頭，被字符檢查擋住
      - POM.XML、MAIN.CFM              → 後綴超過3字母或非市場後綴，被正規表達式擋住
      - ../../etc/passwd               → 含斜線，被字符檢查擋住
      - <script>alert(1)</script>      → 含 < >，被字符檢查擋住
      - 超長字串攻擊                    → 長度限制擋住

    回傳 True = 合法，可繼續處理
    回傳 False = 非法，直接 abort(404)
    """
    if not raw or len(raw) > 12:
        return False
    # 只允許英文字母、數字、點號
    if not re.match(r'^[A-Za-z0-9.]+$', raw):
        return False
    # 點號不可在開頭（擋住 .env 類攻擊）
    if raw.startswith('.'):
        return False
    return bool(_TICKER_PATTERN.match(raw.upper()))


# ============================================================================
# 工具函數
# ============================================================================

def resolve_ticker(raw: str) -> str:
    """
    將用戶輸入解析成 JSON 資料庫的官方代碼（canonical ticker）。
    例如：1398 → 01398.HK、700 → 0700.HK
    找不到時保留 normalize_ticker 的結果（美股等）。
    """
    normalized = normalize_ticker(raw)
    canonical  = get_canonical_ticker(normalized) or get_canonical_ticker(raw)
    return canonical if canonical else normalized


# ============================================================================
# Gemini API
# ============================================================================

def call_gemini_api(prompt: str, use_search: bool = True) -> str:
    """調用 Gemini API，支援聯網搜索"""
    config_params: dict = {
        "temperature": 0.7,
        "max_output_tokens": Config.API_MAX_TOKENS,
    }
    if use_search:
        config_params["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    config = types.GenerateContentConfig(**config_params)

    for attempt in range(Config.API_MAX_RETRIES + 1):
        try:
            response = gemini_client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            return response.text if response.text else "⚠️ API 回覆為空或被安全過濾。"
        except Exception as e:
            print(f"[Gemini] Error (attempt {attempt + 1}): {e}")
            if attempt < Config.API_MAX_RETRIES:
                time.sleep(Config.API_RETRY_DELAY)
    return "⚠️ API 請求失敗。"


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def home():
    return redirect(f'/{Config.DEFAULT_TICKER}')


# ── Admin 路由必須在萬用路由 /<ticker_raw> 之前定義 ──────
# 否則 /admin 會被當成股票代碼處理，顯示「無效股票代碼」錯誤頁
@app.route('/admin')
def admin_root():
    from admin_auth import verify_admin_session
    token = request.cookies.get('admin_token')
    if verify_admin_session(token):
        return redirect('/admin/dashboard')
    return redirect('/admin/login')


@app.route('/<ticker_raw>')
def index(ticker_raw: str):
    """
    股票分析主頁

    安全處理流程：
      1. 靜態資源黑名單      → abort(404)，靜默拒絕
      2. Ticker 格式白名單   → abort(404)，靜默拒絕
         （.env / POM.XML / MAIN.CFM 等惡意掃描全部在此被擋）
      3. 解析成官方代碼
      4. 301 跳轉到標準 URL
      5. 讀取 / 建立快取
    """

    # ── 第一層：靜態資源黑名單 ────────────────────────────────
    if ticker_raw.lower() in _STATIC_BLACKLIST:
        abort(404)

    # ── 第二層：格式白名單（核心安全防護）────────────────────
    # 非合法 ticker 格式 → 直接 404，不渲染任何頁面
    # 這樣駭客收到的是空白 404，無法得知你用的是什麼技術棧
    if not is_valid_ticker(ticker_raw):
        abort(404)

    # ── 第三層：解析成官方代碼（BUG-001 修復）───────────────
    ticker = resolve_ticker(ticker_raw)

    # ── 第四層：301 跳轉到標準 URL ───────────────────────────
    if ticker != ticker_raw.upper():
        return redirect(f'/{ticker}', code=301)

    # ── 讀取快取 ─────────────────────────────────────────────
    stock_info = get_stock(ticker)

    if stock_info:
        print(f"[Cache] 從快取讀取基本資料 {ticker}")
        stock_name   = stock_info['stock_name']
        chinese_name = stock_info['chinese_name']
    else:
        stock_name, exchange = get_stock_info(ticker)

        if stock_name is None:
            # 合法格式但資料庫查無此股票 → 顯示友善錯誤頁面
            return render_template('error.html', ticker=ticker_raw, date=get_today()), 404

        chinese_name = stock_name
        save_stock(ticker=ticker, stock_name=stock_name,
                   chinese_name=chinese_name, exchange=exchange)
        print(f"[Cache] 儲存新股票基本資料 {ticker} → cache/")

    cached_sections_html = {
        key: html
        for key in VALID_SECTIONS
        if (html := get_section_html(ticker, key))
    }

    return render_template(
        'index.html',
        ticker=ticker,
        stock_name=stock_name,
        chinese_name=chinese_name,
        m={"eps": "-", "pe": "-", "yield": "-", "short": "-", "cap": "-", "vol": "-"},
        date=get_today(),
        sections=prompt_manager.get_section_names(),
        cached_sections=cached_sections_html or None,
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

    raw_ticker   = request.json.get('ticker', '')
    force_update = request.json.get('force_update', False)

    # ── API 端同樣做格式驗證，防止繞過前端直接攻擊 API ───────
    if not is_valid_ticker(raw_ticker):
        return jsonify({"success": False, "error": "無效的股票代碼格式"}), 400

    ticker = resolve_ticker(raw_ticker)

    if not force_update:
        cached_html = get_section_html(ticker, section)
        if cached_html:
            print(f"[Cache] 從快取讀取 {ticker} - {section}")
            return jsonify({"success": True, "report": cached_html, "from_cache": True})

    stock_name, exchange = get_stock_info(ticker)
    if stock_name is None:
        return jsonify({"success": False, "error": f"找不到 {ticker} 的資料"})

    chinese_name = stock_name
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

        html_content = markdown.markdown(
            response_text,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        save_section_html(ticker, section, html_content)
        print(f"[Cache] 已儲存 {ticker} - {section} → cache/{ticker}/{section}.html")

        return jsonify({"success": True, "report": html_content, "from_cache": False})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})




# ============================================================================
# Admin 路由（登入 / 後台 / 登出 / Prompt 編輯）
# ============================================================================

from admin_auth import (
    verify_admin_password, create_admin_session,
    delete_admin_session, admin_required, verify_admin_session
)
from database import init_db

# 啟動時建立資料庫表格
init_db()


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if verify_admin_password(password):
            token    = create_admin_session()
            response = make_response(redirect('/admin/dashboard'))
            response.set_cookie(
                'admin_token', token,
                httponly=True, samesite='Lax', max_age=86400
            )
            return response
        error = '密碼錯誤，請重試。'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    token = request.cookies.get('admin_token')
    if token:
        delete_admin_session(token)
    response = make_response(redirect('/admin/login'))
    response.delete_cookie('admin_token')
    return response


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    sections    = prompt_manager.get_section_names()
    cache_count = 0
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'cache')):
        cache_count = sum(
            1 for d in os.listdir(os.path.join(os.path.dirname(__file__), 'cache'))
            if os.path.isdir(os.path.join(os.path.dirname(__file__), 'cache', d))
        )
    return render_template('admin/dashboard.html',
                           sections=sections,
                           cache_count=cache_count)


@app.route('/admin/prompts/<section_key>', methods=['GET', 'POST'])
@admin_required
def admin_prompt_editor(section_key: str):
    sections = prompt_manager.get_section_names()
    if section_key not in sections:
        abort(404)

    msg = None
    if request.method == 'POST':
        new_prompt = request.form.get('prompt_content', '')
        prompt_manager.update_section_prompt(section_key, new_prompt)
        msg = '已儲存'

    current_prompt = prompt_manager.get_section_prompt(section_key)
    return render_template('admin/prompt_editor.html',
                           section_key=section_key,
                           section_name=sections[section_key],
                           prompt_content=current_prompt,
                           sections=sections,
                           msg=msg)


@app.route('/admin/prompts/<section_key>/save', methods=['POST'])
@admin_required
def admin_save_prompt(section_key: str):
    """儲存編輯後的 prompt 內容到 prompts.yaml"""
    sections = prompt_manager.get_section_names()
    if section_key not in sections:
        return jsonify({"success": False, "error": "找不到此 section"}), 404

    new_content = request.json.get('content', '')
    if not new_content.strip():
        return jsonify({"success": False, "error": "Prompt 內容不可為空"})

    try:
        prompt_manager.update_section_prompt(section_key, new_content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/admin/resolve_vars', methods=['POST'])
@admin_required
def admin_resolve_vars():
    """
    查詢某個股票代碼對應的所有變數實際值
    供 Prompt 編輯頁的「查詢變數值」功能使用
    """
    raw_ticker = request.json.get('ticker', '').strip()
    if not raw_ticker:
        return jsonify({"success": False, "error": "請輸入股票代碼"})

    ticker     = resolve_ticker(raw_ticker)
    stock_name, exchange = get_stock_info(ticker)

    if stock_name is None:
        return jsonify({"success": False, "error": f"找不到 {raw_ticker} 的資料"})

    # 取得 exchange context（幣值、資料來源等）
    ctx = prompt_manager._get_exchange_context(exchange)

    variables = {
        "ticker":         ticker,
        "stock_name":     stock_name,
        "chinese_name":   stock_name,
        "exchange":       exchange,
        "today":          get_today(),
        "currency":       ctx.get("currency", ""),
        "data_source":    ctx.get("data_source", ""),
        "legal_focus":    ctx.get("legal_focus", ""),
        "extra_analysis": ctx.get("extra_analysis", ""),
    }

    return jsonify({
        "success":   True,
        "ticker":    ticker,
        "stock_name": stock_name,
        "exchange":  exchange,
        "variables": variables,
    })


@app.route('/admin/prompts/<section_key>/preview', methods=['POST'])
@admin_required
def admin_preview_prompt(section_key: str):
    """
    用當前編輯中的 prompt 內容（未儲存）對指定股票執行 AI 預覽
    供 Prompt 編輯頁的「執行預覽」功能使用
    """
    data       = request.json
    raw_ticker = data.get('ticker', '').strip()
    content    = data.get('content', '').strip()

    if not raw_ticker:
        return jsonify({"success": False, "error": "請輸入股票代碼"})
    if not content:
        return jsonify({"success": False, "error": "Prompt 內容不可為空"})

    ticker     = resolve_ticker(raw_ticker)
    stock_name, exchange = get_stock_info(ticker)

    if stock_name is None:
        return jsonify({"success": False, "error": f"找不到 {raw_ticker} 的資料"})

    # 取得 exchange context 並替換變數
    ctx = prompt_manager._get_exchange_context(exchange)
    variables = {
        "ticker":         ticker,
        "stock_name":     stock_name,
        "chinese_name":   stock_name,
        "exchange":       exchange,
        "today":          get_today(),
        "currency":       ctx.get("currency", ""),
        "data_source":    ctx.get("data_source", ""),
        "legal_focus":    ctx.get("legal_focus", ""),
        "extra_analysis": ctx.get("extra_analysis", ""),
    }

    # 組裝完整 prompt（使用編輯中的內容，不從 YAML 讀取）
    global_cfg  = prompt_manager._config.get('global', {})
    system_role = global_cfg.get('system_role', '')
    format_rules = global_cfg.get('format_rules', '')
    full_prompt = f"{system_role}\n\n{content}\n\n{format_rules}"
    for key, val in variables.items():
        full_prompt = full_prompt.replace(f'{{{key}}}', str(val))

    try:
        response_text = call_gemini_api(full_prompt, use_search=True)
        html_content  = markdown.markdown(
            response_text,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        return jsonify({
            "success":    True,
            "html":       html_content,
            "ticker":     ticker,
            "stock_name": stock_name,
            "exchange":   exchange,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
