/* ================================================================
   terminal.js - 分析終端 JavaScript
   ================================================================
   適用於：index.html（主分析頁面）

   依賴：
     - 頁面需有 data-ticker 屬性在 <body> 上
     - DOM 元素 ID 規則：dot-{id}, preview-{id}, btn-{id},
                         update-{id}, badge-{id}
     - index.html 內需有 id="header-chinese-name", "header-en-name"
     - index.html 內需有 id="popup-container"

   函數索引：
     1. fetchSection()      — 呼叫 API 取得分析報告
     2. updateSection()     — 強制重新分析
     3. openPopUp()         — 開啟彈出報告視窗
     4. toggleMinimize()    — 視窗最小化切換
     5. toggleMaximize()    — 視窗最大化切換
     6. startDrag()         — 視窗拖曳系統
     7. navigateToStock()   — Optimistic UI 切換股票
   ================================================================ */


/* ==========================================================
   全域變數
   ========================================================== */
let analysisCache  = {};   // 儲存各模組的 HTML 報告內容
let _fetchRequestId = 0;   // 競態保護：navigateToStock 時遞增，舊回應自動丟棄

// 從 <body data-ticker="NVDA"> 讀取初始股票代碼
const TICKER = document.body.dataset.ticker || '';

// 從 <body data-lang="zh_hk"> 讀取語言
const LANG = document.body.dataset.lang || 'zh_hk';

// 從 <body data-i18n='...'> 讀取翻譯字典
const I18N = (function() {
    try {
        return JSON.parse(document.body.dataset.i18n || '{}');
    } catch(e) {
        return {};
    }
})();

// 取得當前 ticker（切換後用 _optimisticTicker 覆蓋）
function getCurrentTicker() {
    return window._optimisticTicker || TICKER;
}

// 所有分析模組 ID
const ALL_SECTIONS = ['biz', 'finance', 'exec', 'call', 'ta_price', 'ta_analyst', 'ta_social'];


/* ==========================================================
   工具函數：從 HTML 報告中提取綜合評分
   ========================================================== */
function extractCompositeScore(htmlReport) {
    /**
     * 提取評分表的綜合評分（最後一行，通常是 **綜合評分** 或 **加權綜合評分**）
     *
     * 改進版本支援多種格式：
     * - 第一列包含關鍵詞，分數在第 2 或第 3 列
     * - 分數可以在任何單元格中
     */

    try {
        const temp = document.createElement('div');
        temp.innerHTML = htmlReport;

        // 尋找所有表格
        const tables = temp.querySelectorAll('table');

        if (tables.length === 0) {
            console.warn('[Score] No tables found in report');
            return null;
        }

        // 掃描每個表格
        for (let table of tables) {
            const rows = table.querySelectorAll('tr');

            // 逆向掃描，從最後一行開始
            for (let i = rows.length - 1; i >= 0; i--) {
                const row = rows[i];
                const cells = row.querySelectorAll('td, th');

                if (cells.length < 2) continue;

                // 獲取每個單元格的文本
                const cellTexts = Array.from(cells).map(c => c.textContent.trim());
                const firstCell = cellTexts[0];

                // 檢查是否是綜合評分行（支援多種語言與變體）
                const compositeScoreKeywords = [
                    // 繁體中文
                    '綜合評分', '加權', '綜合情緒',
                    // 簡體中文
                    '综合评分', '综合情绪',
                    // 英文
                    'composite', 'overall', 'combined', 'weighted'
                ];

                const isCompositeScoreLine = compositeScoreKeywords.some(keyword =>
                    firstCell.toLowerCase().includes(keyword.toLowerCase())
                );

                if (isCompositeScoreLine) {
                    // 嘗試從所有單元格中提取分數
                    for (let j = 1; j < cellTexts.length; j++) {
                        const cellText = cellTexts[j];
                        const scoreMatch = cellText.match(/\d+(?:\.\d+)?/);

                        if (scoreMatch) {
                            const score = parseFloat(scoreMatch[0]);
                            if (score >= 1 && score <= 10) {
                                console.log(`[Score] Found: ${score} from cell ${j}`);
                                return Math.round(score * 10) / 10;
                            }
                        }
                    }
                }
            }
        }

        console.warn('[Score] No composite score found in tables');
        return null;

    } catch (error) {
        console.error('[Score] Error extracting score:', error);
        return null;
    }
}


/* ==========================================================
   頁面載入：自動觸發全部分析模組
   ========================================================== */
window.onload = function () {
    ALL_SECTIONS.forEach(id => fetchSection(id));
};


/* ==========================================================
   1. fetchSection — 呼叫後端 API 取得分析報告
   ----------------------------------------------------------
   參數：
     sectionId   (str)  : 分析模組 ID，如 'biz', 'finance'
     forceUpdate (bool) : 是否強制重新生成（略過快取）

   流程：
     1. 顯示載入動畫（金色脈衝）
     2. POST /analyze/<sectionId>
     3. 成功 → 預覽文字 + 「開啟報告」+ 「重新分析」
     4. 失敗 → 錯誤訊息 + 紅色指示燈
   ========================================================== */
async function fetchSection(sectionId, forceUpdate = false) {
    const dot       = document.getElementById(`dot-${sectionId}`);
    const preview   = document.getElementById(`preview-${sectionId}`);
    const btn       = document.getElementById(`btn-${sectionId}`);
    const updateBtn = document.getElementById(`update-${sectionId}`);
    const badge     = document.getElementById(`badge-${sectionId}`);
    const score     = document.getElementById(`score-${sectionId}`);

    // DOM 元素不存在時跳過（避免 crash）
    if (!dot || !preview) return;

    // 記錄此次請求的 ID，用於競態保護
    const myRequestId = _fetchRequestId;

    // 進入載入狀態
    dot.className = 'loading-pulse';
    if (badge)     badge.innerHTML = '';
    if (score)     score.classList.add('hidden');  // ← 隱藏舊排名
    if (updateBtn) updateBtn.disabled = true;

    // 動態載入訊息（每 3 秒切換）
    const loadingMessages = I18N.loading_msgs || ['Loading...', 'Analyzing...', 'Almost done!', 'Coming right up!'];
    let msgIndex = 0;
    preview.innerHTML = loadingMessages[0];
    const msgTimer = setInterval(() => {
        if (msgIndex < loadingMessages.length - 1) {
            msgIndex++;
            preview.innerHTML = loadingMessages[msgIndex];
        }
    }, 3000);

    try {
        const response = await fetch(`/analyze/${sectionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticker: getCurrentTicker(),
                force_update: forceUpdate,
                lang: LANG
            })
        });
        const data = await response.json();
        clearInterval(msgTimer);

        // 競態保護：若期間已切換股票，丟棄此舊回應
        if (myRequestId !== _fetchRequestId) return;

        if (data.success) {
            // ✅ 成功
            analysisCache[sectionId] = data.report;

            // 擷取純文字作為預覽
            const temp = document.createElement('div');
            temp.innerHTML = data.report;
            preview.innerText = temp.innerText.substring(0, 200);
            preview.classList.remove('italic', 'text-gray-400');
            preview.classList.add('text-gray-600');

            dot.className = 'w-2 h-2 rotate-45 bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]';
            if (btn) btn.classList.remove('hidden');

            // 提取並顯示綜合評分
            const scoreElement = document.getElementById(`score-${sectionId}`);
            if (scoreElement) {
                const score = extractCompositeScore(data.report);
                console.log(`[${sectionId}] Score extraction result:`, score);
                console.log(`[${sectionId}] Report preview (first 500 chars):`, data.report.substring(0, 500));

                if (score !== null) {
                    scoreElement.textContent = score;
                    scoreElement.classList.remove('hidden');
                    console.log(`[${sectionId}] ✓ Score displayed: ${score}`);
                } else {
                    scoreElement.classList.add('hidden');
                    console.log(`[${sectionId}] ✗ No score found`);
                }
            }

            // 快取標記
            if (badge) {
                const cacheLabel = I18N.cache_label || 'Cached';
                const freshLabel = I18N.fresh_label || 'AI Live';
                badge.innerHTML = (data.from_cache && !forceUpdate)
                    ? `<span class="cache-badge cached">${cacheLabel}</span>`
                    : `<span class="cache-badge fresh">${freshLabel}</span>`;
            }

        } else {
            // ❌ API 回傳失敗
            preview.innerHTML = data.error || 'Analysis failed, please retry';
            dot.className = 'w-2 h-2 rotate-45 bg-red-500';
            if (updateBtn) updateBtn.disabled = false;
        }

    } catch (e) {
        clearInterval(msgTimer);
        // ❌ 網絡錯誤
        if (myRequestId !== _fetchRequestId) return; // 切換中，靜默丟棄
        preview.innerHTML = 'Connection error, please retry';
        dot.className = 'w-2 h-2 rotate-45 bg-red-500';
        if (updateBtn) updateBtn.disabled = false;
    }
}


/* ==========================================================
   2. updateSection — 強制重新分析
   ========================================================== */
async function updateSection(sectionId) {
    if (!confirm(I18N.confirm_reanalyze || 'Re-analyze this section?\n\n⚠️ This will call the AI API.')) return;

    const updateBtn = document.getElementById(`update-${sectionId}`);
    const originalText = updateBtn.textContent;
    updateBtn.textContent = I18N.updating || 'Updating...';
    updateBtn.disabled = true;

    await fetchSection(sectionId, true);

    updateBtn.textContent = I18N.updated || '✅ Updated';
    setTimeout(() => { updateBtn.textContent = originalText; }, 2000);
}


/* ==========================================================
   3. openPopUp — 開啟彈出報告視窗
   ========================================================== */
function openPopUp(id, title) {
    // 同一模組視窗已存在則先關閉
    const existing = document.getElementById(`win-${id}`);
    if (existing) existing.remove();

    const win = document.createElement('div');
    win.id = `win-${id}`;
    win.className = 'draggable-window';
    win.style.top  = '7.5vh';
    win.style.left = '7.5vw';

    win.innerHTML = `
        <div class="window-header" onmousedown="startDrag(event, 'win-${id}')">
            <div class="window-header-left">
                <div class="window-header-icon"></div>
                <span class="window-header-title">${title}</span>
                <span class="window-header-tag">// ${getCurrentTicker()} ${I18N.smart_terminal || 'AI Terminal'}</span>
            </div>
            <div class="window-controls">
                <button class="window-ctrl-btn btn-minimize desktop-only" onclick="toggleMinimize('win-${id}')" title="${I18N.btn_minimize || 'Minimize'}">
                    <svg viewBox="0 0 16 16"><line x1="3" y1="8" x2="13" y2="8"/></svg>
                </button>
                <div class="window-ctrl-divider desktop-only"></div>
                <button class="window-ctrl-btn btn-maximize desktop-only" onclick="toggleMaximize('win-${id}')" title="${I18N.btn_maximize || 'Maximize'}">
                    <svg viewBox="0 0 16 16"><rect x="2.5" y="2.5" width="11" height="11" rx="1"/></svg>
                </button>
                <div class="window-ctrl-divider desktop-only"></div>
                <button class="window-ctrl-btn btn-close" onclick="document.getElementById('win-${id}').remove()" title="${I18N.btn_close || 'Close'}">
                    <svg viewBox="0 0 16 16"><line x1="3" y1="3" x2="13" y2="13"/><line x1="13" y1="3" x2="3" y2="13"/></svg>
                </button>
            </div>
        </div>
        <div class="window-body">
            <div class="max-w-4xl mx-auto py-4">
                ${analysisCache[id] || `<p style="color:#999;">${I18N.no_data || 'No data available'}</p>`}
            </div>
        </div>
        <!-- 懸浮面板（只在手機版顯示） -->
        <div class="floating-panel mobile-only">
            <button class="floating-btn scroll-to-top" title="${I18N.btn_scroll_top || 'Back to top'}">
                <svg viewBox="0 0 24 24" width="20" height="20"><path d="M7 14l5-5 5 5z" fill="currentColor"/></svg>
            </button>
            <button class="floating-btn share-btn" title="${I18N.btn_share || 'Share'}">
                <svg viewBox="0 0 24 24" width="20" height="20"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.15c.52.47 1.2.77 1.96.77 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.82 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.82 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z" fill="currentColor"/></svg>
            </button>
            <button class="floating-btn close-btn" title="${I18N.btn_close || 'Close'}">
                <svg viewBox="0 0 24 24" width="20" height="20"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z" fill="currentColor"/></svg>
            </button>
        </div>`;

    document.getElementById('popup-container').appendChild(win);

    // 把所有 <table> 包上 .table-wrapper，實現手機橫向捲動
    win.querySelectorAll('.window-body table').forEach(table => {
        if (table.parentElement.classList.contains('table-wrapper')) return;
        const wrapper = document.createElement('div');
        wrapper.className = 'table-wrapper';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });

    // 進度條：更新用戶滑動進度（SVG 動態版）
    const windowBody = win.querySelector('.window-body');
    const windowHeader = win.querySelector('.window-header');
    const floatingPanel = win.querySelector('.floating-panel');
    const scrollToTopBtn = win.querySelector('.scroll-to-top');
    const shareBtn = win.querySelector('.share-btn');
    const closeBtnFloating = win.querySelector('.floating-panel .close-btn');

    // 在 header 下方插入進度條（CSS div 版）
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar-track';
    const progressFill = document.createElement('div');
    progressFill.className = 'progress-bar-fill';
    progressBar.appendChild(progressFill);
    windowHeader.insertAdjacentElement('afterend', progressBar);

    windowBody.addEventListener('scroll', () => {
        const scrolled = windowBody.scrollTop;
        const scrollHeight = windowBody.scrollHeight - windowBody.clientHeight;
        const scrollPercent = scrollHeight > 0 ? (scrolled / scrollHeight) * 100 : 0;

        // 更新進度條寬度
        progressFill.style.width = scrollPercent + '%';

        // 懸浮面板：滑超過 300px 時淡入
        if (scrolled > 300) {
            floatingPanel.classList.add('visible');
        } else {
            floatingPanel.classList.remove('visible');
        }
    }, { passive: true });

    // 懸浮面板事件：回到頂部
    if (scrollToTopBtn) {
        scrollToTopBtn.addEventListener('click', () => {
            windowBody.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // 懸浮面板事件：分享
    if (shareBtn) {
        shareBtn.addEventListener('click', () => {
            const shareTextTpl = I18N.share_text || 'View {ticker} {title} analysis';
            const shareText = shareTextTpl.replace('{ticker}', getCurrentTicker()).replace('{title}', title);
            const shareData = {
                title: title,
                text: shareText,
                url: window.location.href
            };

            const fallbackCopy = () => {
                const copiedMsg   = I18N.copied      || 'Copied to clipboard';
                const manualMsg   = I18N.copy_manual || 'Please copy manually: ';
                try {
                    navigator.clipboard.writeText(`${shareData.text}\n${shareData.url}`)
                        .then(() => alert(copiedMsg))
                        .catch(() => alert(manualMsg + shareData.url));
                } catch {
                    alert(manualMsg + shareData.url);
                }
            };

            if (navigator.share) {
                navigator.share(shareData).catch(fallbackCopy);
            } else {
                fallbackCopy();
            }
        });
    }

    // 懸浮面板事件：關閉
    if (closeBtnFloating) {
        closeBtnFloating.addEventListener('click', () => {
            win.remove();
        });
    }

    // 手機版：添加 swipe-down 關閉手勢（只在 scrollTop === 0 時啟用，避免與內容滾動衝突）
    const isMobile = window.matchMedia('(max-width: 640px)').matches;
    if (isMobile) {
        let touchStartY = 0, swipeMoved = false;

        win.addEventListener('touchstart', (e) => {
            touchStartY = e.touches[0].clientY;
            swipeMoved = false;
        }, { passive: true });

        win.addEventListener('touchmove', (e) => {
            // 只在內容尚未滾動時才允許 swipe 關閉（scrollTop === 0）
            if (swipeMoved || windowBody.scrollTop > 0) return;

            const deltaY = e.touches[0].clientY - touchStartY;

            // 如果向下滑超過 80px，標記 swipeMoved
            if (deltaY > 80) {
                swipeMoved = true;
                win.style.opacity = `${1 - deltaY / 300}`;  // 漸褪淡出效果
            }
        }, { passive: true });

        win.addEventListener('touchend', (e) => {
            const deltaY = e.changedTouches[0].clientY - touchStartY;

            if (deltaY > 80 && windowBody.scrollTop === 0) {
                // 向下滑超過 80px 且未滾動：關閉
                win.remove();
            } else {
                // 未達閥值或已滾動：復原
                win.style.opacity = '1';
            }
        }, { passive: true });
    }
}


/* ==========================================================
   4. toggleMinimize — 最小化切換
   ========================================================== */
function toggleMinimize(winId) {
    const win = document.getElementById(winId);
    if (!win) return;
    if (win.classList.contains('maximized')) win.classList.remove('maximized');
    win.classList.toggle('minimized');

    const minBtn = win.querySelector('.btn-minimize svg');
    minBtn.innerHTML = win.classList.contains('minimized')
        ? '<polyline points="3 11 8 6 13 11"/>'
        : '<line x1="3" y1="8" x2="13" y2="8"/>';
}


/* ==========================================================
   5. toggleMaximize — 最大化切換
   關鍵：用 inline style 覆蓋 CSS 的 max-width
   ========================================================== */
function toggleMaximize(winId) {
    const win = document.getElementById(winId);
    if (!win) return;

    // 若已最小化，先還原
    if (win.classList.contains('minimized')) {
        win.classList.remove('minimized');
        win.querySelector('.btn-minimize svg').innerHTML = '<line x1="3" y1="8" x2="13" y2="8"/>';
    }

    const isMaximized = win.classList.toggle('maximized');

    if (isMaximized) {
        win.dataset.prevTop  = win.style.top;
        win.dataset.prevLeft = win.style.left;
        win.style.top         = '0px';
        win.style.left        = '0px';
        win.style.width       = '100vw';
        win.style.height      = '100vh';
        win.style.maxWidth    = '100vw';
        win.style.borderRadius = '0';
    } else {
        win.style.top         = win.dataset.prevTop  || '7.5vh';
        win.style.left        = win.dataset.prevLeft || '7.5vw';
        win.style.width       = '';
        win.style.height      = '';
        win.style.maxWidth    = '';
        win.style.borderRadius = '';
    }

    win.querySelector('.btn-maximize svg').innerHTML = isMaximized
        ? '<rect x="4.5" y="1.5" width="10" height="10" rx="1"/><rect x="1.5" y="4.5" width="10" height="10" rx="1"/>'
        : '<rect x="2.5" y="2.5" width="11" height="11" rx="1"/>';
}


/* ==========================================================
   6. 拖曳系統（requestAnimationFrame 高效能版）
   ========================================================== */
let dragObj = null, offX = 0, offY = 0, rafId = null, lastX = 0, lastY = 0;

function startDrag(e, id) {
    if (e.target.closest('.window-controls')) return;
    const win = document.getElementById(id);
    if (win.classList.contains('maximized') || win.classList.contains('minimized')) return;

    dragObj = win;
    document.querySelectorAll('.draggable-window').forEach(w => w.style.zIndex = 1000);
    dragObj.style.zIndex    = 1001;
    dragObj.style.willChange = 'left, top';
    offX = e.clientX - dragObj.offsetLeft;
    offY = e.clientY - dragObj.offsetTop;

    document.onmousemove = (ev) => {
        ev.preventDefault();
        lastX = ev.clientX;
        lastY = ev.clientY;
        if (!rafId) rafId = requestAnimationFrame(updateDrag);
    };
    document.onmouseup = () => {
        if (dragObj) dragObj.style.willChange = 'auto';
        dragObj = null;
        rafId   = null;
        document.onmousemove = null;
        document.onmouseup   = null;
    };
}

function updateDrag() {
    if (dragObj) {
        dragObj.style.left = (lastX - offX) + 'px';
        dragObj.style.top  = (lastY - offY) + 'px';
    }
    rafId = null;
}


/* ==========================================================
   7. navigateToStock — Optimistic UI 切換股票
   ----------------------------------------------------------
   流程：
     1. 立即更新 header 名稱（零延遲感）
     2. 所有卡片顯示 skeleton loading
     3. 清空快取，更新 ticker，重新觸發全部分析
   ========================================================== */
async function navigateToStock(code, name) {
    // ── 1. 立即更新 header ───────────────────────────────────
    const elChineseName = document.getElementById('header-chinese-name');
    const elEnName      = document.getElementById('header-en-name');

    if (elChineseName) {
        elChineseName.style.opacity = '0';
        setTimeout(() => {
            elChineseName.textContent = name || code;
            elChineseName.style.opacity = '1';
        }, 150);
    }
    if (elEnName) {
        elEnName.style.opacity = '0';
        setTimeout(() => {
            elEnName.textContent = code;   // 只顯示股票代碼
            elEnName.style.opacity = '1';
        }, 150);
    }

    document.title = `${name || code} ${I18N.terminal_title || 'Investment Decision Terminal'} | Aurum Intelligence`;
    history.pushState({ code, name }, '', `/${code}`);

    // ── 2. 所有卡片進入 skeleton 狀態 ────────────────────────
    ALL_SECTIONS.forEach(id => {
        const dot     = document.getElementById(`dot-${id}`);
        const preview = document.getElementById(`preview-${id}`);
        const btn     = document.getElementById(`btn-${id}`);
        const badge   = document.getElementById(`badge-${id}`);

        if (dot)     dot.className = 'loading-pulse';
        if (btn)     btn.classList.add('hidden');
        if (badge)   badge.innerHTML = '';
        if (preview) preview.innerHTML = `
            <div class="skeleton-line" style="width:88%"></div>
            <div class="skeleton-line" style="width:65%;margin-top:7px"></div>
            <div class="skeleton-line" style="width:78%;margin-top:7px"></div>`;
    });

    // 關閉所有彈出視窗
    document.querySelectorAll('.draggable-window').forEach(w => w.remove());

    // ── 3. 更新 ticker，令舊請求失效，重新分析 ───────────────
    analysisCache         = {};
    window._optimisticTicker = code;
    _fetchRequestId++;             // 令所有 in-flight 舊請求失效

    ALL_SECTIONS.forEach(id => fetchSection(id));
}

// 瀏覽器上下頁（← →）支援
window.addEventListener('popstate', () => window.location.reload());
