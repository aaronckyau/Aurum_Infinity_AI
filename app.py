"""
Stock Analyzer - 主程式（Google Gemini 3 Flash 版本 + 靜態 HTML 快取）
============================================================================
URL 結構：
  /                    → 跳轉到預設標的（NVDA）
  /AAPL                → 蘋果股票分析頁
  /admin               → 後台首頁（需登入）
  /admin/login         → Admin 登入
  /admin/prompts/<key> → 編輯指定 Prompt
============================================================================
"""
from dotenv import load_dotenv
import os
import time
import glob
from datetime import datetime

import markdown
import yaml
from flask import Flask, render_template, request, jsonify, redirect, make_response

from google import genai
from google.genai import types

from prompt_manager import PromptManager
from file_cache import (
    get_stock, get_section_html, save_stock, save_section_html, VALID_SECTIONS
)
from read_stock_code import normalize_ticker, get_stock_info, search_stocks
from logger import get_logger, log_route, Timer
from database import init_db
from admin_auth import verify_admin_password, create_admin_session, \
                       verify_admin_session, delete_admin_session, admin_required

# ============================================================================
# 初始化
# ============================================================================
load_dotenv()
init_db()   # 啟動時自動建立資料庫


class Config:
    GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL    = "gemini-3-flash-preview"
    DEFAULT_TICKER  = 'NVDA'
    PROMPTS_PATH    = os.path.join(os.path.dirname(__file__), 'prompts', 'prompts.yaml')
    API_MAX_TOKENS  = 8000
    API_MAX_RETRIES = 2
    API_RETRY_DELAY = 5


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

log = get_logger(__name__)
log.info("=" * 60)
log.info("Aurum Intelligence Stock Analyzer 啟動中...")
log.info(f"模型：{Config.GEMINI_MODEL}")
log.info("=" * 60)


def get_today() -> str:
    return datetime.now().strftime('%Y/%m/%d')


# ============================================================================
# 初始化 Gemini + PromptManager
# ============================================================================
try:
    gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
    log.info("✓ Gemini Client 初始化成功")
except Exception as e:
    log.critical(f"✗ Gemini Client 初始化失敗: {e}", exc_info=True)
    raise

try:
    prompt_manager = PromptManager(Config.PROMPTS_PATH)
    log.info("✓ PromptManager 初始化成功")
except Exception as e:
    log.critical(f"✗ PromptManager 初始化失敗: {e}", exc_info=True)
    raise


# ============================================================================
# Gemini API
# ============================================================================

def call_gemini_api(prompt: str, use_search: bool = True) -> str:
    config_params = {
        "temperature": 0.7,
        "max_output_tokens": Config.API_MAX_TOKENS,
    }
    if use_search:
        config_params["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    config = types.GenerateContentConfig(**config_params)

    for attempt in range(Config.API_MAX_RETRIES + 1):
        try:
            log.debug(f"Gemini API 請求（attempt {attempt + 1}）")
            with Timer(log, f"Gemini API attempt {attempt + 1}"):
                response = gemini_client.models.generate_content(
                    model=Config.GEMINI_MODEL,
                    contents=prompt,
                    config=config,
                )
            if response.text:
                return response.text
            else:
                log.warning("Gemini API 回覆為空")
                return "⚠️ API 回覆為空或被安全過濾。"

        except Exception as e:
            log.warning(f"Gemini API 錯誤 (attempt {attempt + 1}): {e}")
            if attempt < Config.API_MAX_RETRIES:
                time.sleep(Config.API_RETRY_DELAY)
                continue
            log.error(f"Gemini API 所有重試失敗: {e}", exc_info=True)
            return f"⚠️ API 錯誤: {str(e)}"

    return "⚠️ API 請求失敗。"


# ============================================================================
# Admin 路由
# ============================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin 登入頁"""
    # 已登入 → 直接跳轉後台
    token = request.cookies.get('admin_token')
    if verify_admin_session(token):
        return redirect('/admin')

    if request.method == 'POST':
        password = request.form.get('password', '')
        if verify_admin_password(password):
            token    = create_admin_session()
            response = make_response(redirect('/admin'))
            # 把 token 存到 Cookie，HttpOnly 防止 JS 讀取（更安全）
            response.set_cookie(
                'admin_token', token,
                max_age = 60 * 60 * 24,   # 24 小時
                httponly = True,
                samesite = 'Lax'
            )
            log.info("[Admin] 登入成功")
            return response
        else:
            log.warning("[Admin] 登入失敗：密碼錯誤")
            return render_template('admin/login.html', error="密碼錯誤，請重試")

    return render_template('admin/login.html', error=None)


@app.route('/admin/logout')
def admin_logout():
    """Admin 登出"""
    token = request.cookies.get('admin_token')
    if token:
        delete_admin_session(token)
    response = make_response(redirect('/admin/login'))
    response.delete_cookie('admin_token')
    log.info("[Admin] 已登出")
    return response


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin 後台首頁"""
    # 統計已快取的股票數量
    cache_dir   = os.path.join(os.path.dirname(__file__), 'cache')
    cache_count = len(glob.glob(os.path.join(cache_dir, '*/info.json')))

    return render_template(
        'admin/dashboard.html',
        sections    = prompt_manager.get_section_names(),
        cache_count = cache_count,
    )


@app.route('/admin/prompts/<section_key>')
@admin_required
def admin_prompt_editor(section_key):
    """Prompt 編輯頁面"""
    # 讀取目前 prompts.yaml
    with open(Config.PROMPTS_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    sections = config.get('sections', {})
    if section_key not in sections:
        log.warning(f"[Admin] 找不到 section: {section_key}")
        return redirect('/admin')

    section_cfg  = sections[section_key]
    section_name = section_cfg.get('name', section_key)
    # 只取 prompt 部分給編輯器
    prompt_content = section_cfg.get('prompt', '')

    return render_template(
        'admin/prompt_editor.html',
        section_key     = section_key,
        section_name    = section_name,
        prompt_content  = prompt_content,
    )


@app.route('/admin/prompts/<section_key>/save', methods=['POST'])
@admin_required
def admin_prompt_save(section_key):
    """儲存修改後的 Prompt 到 prompts.yaml"""
    try:
        new_content = request.json.get('content', '')

        # 讀取現有 yaml
        with open(Config.PROMPTS_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if section_key not in config.get('sections', {}):
            return jsonify({"success": False, "error": f"找不到 section: {section_key}"})

        # 只更新 prompt 欄位，其他設定保持不變
        config['sections'][section_key]['prompt'] = new_content

        # 寫回 yaml（保留格式）
        with open(Config.PROMPTS_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True,
                      default_flow_style=False, sort_keys=False)

        # 通知 prompt_manager 重新載入
        prompt_manager._config = prompt_manager._load_yaml()
        log.info(f"[Admin] Prompt 已更新: {section_key}")

        return jsonify({"success": True})

    except Exception as e:
        log.error(f"[Admin] 儲存 Prompt 失敗: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route('/admin/prompts/<section_key>/preview', methods=['POST'])
@admin_required
def admin_prompt_preview(section_key):
    """用指定股票代碼測試 Prompt 效果，回傳 AI 生成的 HTML"""
    try:
        custom_prompt_content = request.json.get('content', '')
        # 從前端接收股票代碼，預設 NVDA
        raw_ticker = request.json.get('ticker', 'NVDA').strip().upper()
        test_ticker = normalize_ticker(raw_ticker)

        # 從本地資料庫查詢股票真實名稱與交易所
        stock_name, exchange = get_stock_info(test_ticker)
        if stock_name is None:
            return jsonify({"success": False, "error": f"找不到股票代碼：{test_ticker}，請確認後重試"})

        # 用 prompt_manager 取得正確的 exchange context（含 normalize）
        exchange_ctx = prompt_manager._get_exchange_context(exchange)

        # 讀取 global 設定組裝完整 prompt
        with open(Config.PROMPTS_PATH, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        system_role  = cfg.get('global', {}).get('system_role', '')
        format_rules = cfg.get('global', {}).get('format_rules', '')
        full_prompt  = f"{system_role}\n\n{custom_prompt_content}\n\n{format_rules}"

        # 替換變數（使用真實股票資料）
        variables = {
            'ticker':       test_ticker,
            'stock_name':   stock_name,
            'exchange':     exchange,
            'today':        get_today(),
            'chinese_name': stock_name,
            **exchange_ctx,
        }
        for k, v in variables.items():
            full_prompt = full_prompt.replace(f'{{{k}}}', str(v))

        log.info(f"[Admin] Preview prompt: {section_key}（使用 {test_ticker} 測試）")
        response_text = call_gemini_api(full_prompt, use_search=False)

        if response_text.startswith("⚠️"):
            return jsonify({"success": False, "error": response_text})

        html = markdown.markdown(
            response_text,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        return jsonify({
            "success":    True,
            "html":       html,
            "ticker":     test_ticker,
            "stock_name": stock_name,
            "exchange":   exchange,
        })

    except Exception as e:
        log.error(f"[Admin] Preview 失敗: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})



@app.route('/admin/resolve_vars', methods=['POST'])
@admin_required
def admin_resolve_vars():
    """
    輸入股票代碼，回傳所有變數的實際值
    讓 Admin 在寫 Prompt 前確認變數內容
    """
    try:
        raw_ticker = request.json.get('ticker', '').strip().upper()
        if not raw_ticker:
            return jsonify({"success": False, "error": "請輸入股票代碼"})

        ticker = normalize_ticker(raw_ticker)
        stock_name, exchange = get_stock_info(ticker)

        if stock_name is None:
            return jsonify({"success": False, "error": f"找不到股票：{ticker}"})

        exchange_ctx = prompt_manager._get_exchange_context(exchange)

        variables = {
            'ticker':         ticker,
            'stock_name':     stock_name,
            'chinese_name':   stock_name,
            'exchange':       exchange,
            'today':          get_today(),
            'data_source':    exchange_ctx.get('data_source', ''),
            'currency':       exchange_ctx.get('currency', ''),
            'legal_focus':    exchange_ctx.get('legal_focus', ''),
            'extra_analysis': exchange_ctx.get('extra_analysis', ''),
        }

        return jsonify({"success": True, "variables": variables, "ticker": ticker})

    except Exception as e:
        log.error(f"[Admin] resolve_vars 失敗: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})

# ============================================================================
# 主要 Routes（原有功能，完全不動）
# ============================================================================

@app.route('/')
def home():
    log.debug(f"根路徑跳轉 → /{Config.DEFAULT_TICKER}")
    return redirect(f'/{Config.DEFAULT_TICKER}')


@app.route('/<ticker_raw>')
@log_route(log)
def index(ticker_raw):
    if ticker_raw.lower() in ('favicon.ico', 'robots.txt', 'sitemap.xml'):
        return '', 404

    ticker = normalize_ticker(ticker_raw)
    if ticker != ticker_raw.upper():
        return redirect(f'/{ticker}', code=301)

    stock_info = get_stock(ticker)
    if stock_info:
        log.info(f"[Cache HIT] {ticker}")
        stock_name   = stock_info['stock_name']
        chinese_name = stock_info['chinese_name']
    else:
        stock_name, exchange = get_stock_info(ticker)
        if stock_name is None:
            log.warning(f"找不到股票: {ticker}")
            return render_template('error.html', ticker=ticker_raw, date=get_today()), 404
        chinese_name = stock_name
        save_stock(ticker=ticker, stock_name=stock_name,
                   chinese_name=chinese_name, exchange=exchange)
        log.info(f"[Cache SAVE] {ticker}")

    cached_sections_html = {}
    for section_key in VALID_SECTIONS:
        html = get_section_html(ticker, section_key)
        if html:
            cached_sections_html[section_key] = html

    log.info(f"快取區塊: {len(cached_sections_html)}/{len(VALID_SECTIONS)}")

    return render_template(
        'index.html',
        ticker          = ticker,
        stock_name      = stock_name,
        chinese_name    = chinese_name,
        m               = {"eps": "-", "pe": "-", "yield": "-",
                           "short": "-", "cap": "-", "vol": "-"},
        date            = get_today(),
        sections        = prompt_manager.get_section_names(),
        cached_sections = cached_sections_html if cached_sections_html else None
    )


@app.route('/api/search_stock')
def search_stock():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    results = search_stocks(query, limit=8)
    return jsonify(results)


@app.route('/analyze/<section>', methods=['POST'])
@log_route(log)
def analyze_section(section):
    if section not in VALID_SECTIONS:
        return jsonify({"success": False, "error": "非法的分析類別"}), 400

    raw_ticker   = request.json.get('ticker', '')
    ticker       = normalize_ticker(raw_ticker)
    force_update = request.json.get('force_update', False)

    if not force_update:
        cached_html = get_section_html(ticker, section)
        if cached_html:
            log.info(f"[Cache HIT] {ticker}/{section}")
            return jsonify({"success": True, "report": cached_html, "from_cache": True})

    stock_name, exchange = get_stock_info(ticker)
    if stock_name is None:
        return jsonify({"success": False, "error": f"找不到 {ticker} 的資料"})

    chinese_name = stock_name
    if not get_stock(ticker):
        save_stock(ticker, stock_name, chinese_name, exchange)

    try:
        with Timer(log, f"建立 Prompt [{ticker}/{section}]"):
            prompt = prompt_manager.build(
                section=section, ticker=ticker, stock_name=stock_name,
                exchange=exchange, today=get_today(), chinese_name=chinese_name,
            )

        log.info(f"[AI] 呼叫 Gemini: {ticker}/{section}")
        with Timer(log, f"Gemini 分析 [{ticker}/{section}]"):
            response_text = call_gemini_api(prompt, use_search=True)

        if response_text.startswith("⚠️"):
            return jsonify({"success": False, "error": response_text})

        html_content = markdown.markdown(
            response_text, extensions=['tables', 'fenced_code', 'nl2br']
        )
        save_section_html(ticker, section, html_content)
        log.info(f"[Cache SAVE] {ticker}/{section}")
        return jsonify({"success": True, "report": html_content, "from_cache": False})

    except Exception as e:
        log.error(f"分析失敗: {ticker}/{section} — {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


# ============================================================================
# 錯誤處理
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    log.warning(f"404: {request.path}")
    return jsonify({"error": "Not Found"}), 404


@app.errorhandler(500)
def server_error(e):
    log.error(f"500: {request.path} — {e}", exc_info=True)
    return jsonify({"error": "Internal Server Error"}), 500


if __name__ == '__main__':
    log.info("以 debug 模式啟動，port=5000")
    app.run(debug=True, port=5000)
