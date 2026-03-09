"""
Translations - 多語言 UI 字串字典
============================================================================
支援語言：
  zh_hk  繁體中文（預設）
  zh_cn  簡體中文
  en     English
============================================================================
"""

TRANSLATIONS: dict = {
    "zh_hk": {
        # Header
        "search_placeholder": "股票代碼或名稱...",
        "search_btn": "查詢",
        "lang_label": "語言",

        # 頁面標題
        "terminal_title": "投資決策終端",

        # 基本面分析區
        "fundamental_title": "基本面決策矩陣",
        "fundamental_label": "基本面分析",
        "card_biz":    "商業模式",  "icon_biz":    "策略",
        "card_exec":   "治理效能",  "icon_exec":   "管理層",
        "card_finance":"財務質量",  "icon_finance":"財務",
        "card_call":   "會議展望",  "icon_call":   "展望",

        # 技術面分析區
        "technical_title": "技術與情緒診斷",
        "technical_label": "市場動態",
        "card_ta_price":   "價格行為",  "icon_ta_price":   "技術面",
        "card_ta_analyst": "市場預測",  "icon_ta_analyst": "分析師",
        "card_ta_social":  "社群情緒",  "icon_ta_social":  "輿情",

        # JS 動態訊息
        "loading_msgs": ["正在收集資料...", "正在分析中...", "快完成了！", "結果馬上就出來啦～"],
        "confirm_reanalyze": "確定要重新分析此區塊嗎？\n\n⚠️ 這將呼叫 AI API 生成最新分析。",
        "updating": "更新中...",
        "updated":  "✅ 已更新",
        "no_data":  "暫無數據",
        "copied":       "已複製到剪貼板",
        "copy_manual":  "請手動複製：",
        "share_text":   "查看 {ticker} 的 {title} 分析",
        "cache_label":  "非即時數據",
        "fresh_label":  "AI 即時分析",
        "init_msg":     "系統初始化中...",
        "standby_msg":  "待命狀態...",
        "smart_terminal": "智能終端",

        # 彈出視窗按鈕 title
        "btn_minimize": "最小化",
        "btn_maximize": "最大化",
        "btn_close":    "關閉",
        "btn_scroll_top": "回到頂部",
        "btn_share":    "分享",

        # 錯誤頁面
        "error_title":       "無效的股票代碼",
        "error_unrecognized": "系統無法識別股票代碼",
        "error_hint":        "請確認代碼是否正確，例如：AAPL、TSLA、NVDA、0700.HK",
        "error_search_placeholder": "重新輸入股票代碼...",
        "error_back_default": "← 返回預設標的",

        # 免責聲明
        "disclaimer_title": "免責聲明與風險披露",
        "disclaimer_body": (
            "本資訊僅為一般通訊，僅供提供資訊及參考之用。其性質屬教育性質，並非旨在作為對任何特定投資產品、"
            "策略、計劃特點或其他目的的意見、建議或推薦，亦不構成 Aureum Infinity Capital Limited（滶盈資本有限公司）"
            "參與本文所述任何交易的承諾。本資訊中所使用的任何例子均屬泛化、假設性及僅供說明用途。本材料並未包含足夠資訊"
            "以支持任何投資決定，閣下不應依賴本資訊來評估投資任何證券或產品的優劣。\n"
            "此外，閣下應自行獨立評估任何投資在法律、監管、稅務、信貸及會計方面的影響，並與閣下自身的專業顧問共同決定，"
            "本資訊所述任何投資是否適合閣下的個人目標。投資者應確保在作出任何投資前，取得所有可取得的相關資訊。\n\n"
            "本資訊所載的任何預測、數字、意見、投資技巧及策略僅供資訊用途，基於若干假設及當前市場狀況，並可於無事先通知下變更。"
            "本資訊所呈現的所有內容，本公司已盡力確保於製作時準確，但並無就其準確性、完整性或及時性作出任何保證，"
            "亦不會就任何錯誤、遺漏或因依賴本資訊而產生的任何損失承擔責任。\n\n"
            "必須注意，投資涉及風險，投資價值及來自投資的收入可能會因市場狀況及稅務協議而波動，"
            "投資者可能無法取回全部投資本金。過往表現及收益率並非當前及未來結果的可靠指標。\n\n"
            "本內容並非針對任何特定司法管轄區的投資者而提供，不同司法管轄區的投資者應自行確保使用本內容符合當地法例及規定。"
            "本公司保留隨時修改、更新或撤回本內容的權利，而毋須事先通知。"
        ),
        "copyright": "© Aurum Infinity Capital Limited  // 版權所有",
    },

    "zh_cn": {
        # Header
        "search_placeholder": "股票代码或名称...",
        "search_btn": "查询",
        "lang_label": "语言",

        # 页面标题
        "terminal_title": "投资决策终端",

        # 基本面分析区
        "fundamental_title": "基本面决策矩阵",
        "fundamental_label": "基本面分析",
        "card_biz":    "商业模式",  "icon_biz":    "策略",
        "card_exec":   "治理效能",  "icon_exec":   "管理层",
        "card_finance":"财务质量",  "icon_finance":"财务",
        "card_call":   "会议展望",  "icon_call":   "展望",

        # 技术面分析区
        "technical_title": "技术与情绪诊断",
        "technical_label": "市场动态",
        "card_ta_price":   "价格行为",  "icon_ta_price":   "技术面",
        "card_ta_analyst": "市场预测",  "icon_ta_analyst": "分析师",
        "card_ta_social":  "社群情绪",  "icon_ta_social":  "舆情",

        # JS 动态消息
        "loading_msgs": ["正在收集数据...", "正在分析中...", "快完成了！", "结果马上就出来啦～"],
        "confirm_reanalyze": "确定要重新分析此区块吗？\n\n⚠️ 这将调用 AI API 生成最新分析。",
        "updating": "更新中...",
        "updated":  "✅ 已更新",
        "no_data":  "暂无数据",
        "copied":       "已复制到剪贴板",
        "copy_manual":  "请手动复制：",
        "share_text":   "查看 {ticker} 的 {title} 分析",
        "cache_label":  "非实时数据",
        "fresh_label":  "AI 实时分析",
        "init_msg":     "系统初始化中...",
        "standby_msg":  "待命状态...",
        "smart_terminal": "智能终端",

        # 弹出窗口按钮 title
        "btn_minimize": "最小化",
        "btn_maximize": "最大化",
        "btn_close":    "关闭",
        "btn_scroll_top": "回到顶部",
        "btn_share":    "分享",

        # 错误页面
        "error_title":        "无效的股票代码",
        "error_unrecognized": "系统无法识别股票代码",
        "error_hint":         "请确认代码是否正确，例如：AAPL、TSLA、NVDA、0700.HK",
        "error_search_placeholder": "重新输入股票代码...",
        "error_back_default": "← 返回默认标的",

        # 免责声明
        "disclaimer_title": "免责声明与风险披露",
        "disclaimer_body": (
            "本资讯仅为一般通讯，仅供提供资讯及参考之用。其性质属教育性质，并非旨在作为对任何特定投资产品、"
            "策略、计划特点或其他目的的意见、建议或推荐，亦不构成 Aureum Infinity Capital Limited（滶盈资本有限公司）"
            "参与本文所述任何交易的承诺。本资讯中所使用的任何例子均属泛化、假设性及仅供说明用途。本材料并未包含足够资讯"
            "以支持任何投资决定，阁下不应依赖本资讯来评估投资任何证券或产品的优劣。\n"
            "此外，阁下应自行独立评估任何投资在法律、监管、税务、信贷及会计方面的影响，并与阁下自身的专业顾问共同决定，"
            "本资讯所述任何投资是否适合阁下的个人目标。投资者应确保在作出任何投资前，取得所有可取得的相关资讯。\n\n"
            "本资讯所载的任何预测、数字、意见、投资技巧及策略仅供资讯用途，基于若干假设及当前市场状况，并可于无事先通知下变更。"
            "本资讯所呈现的所有内容，本公司已尽力确保于制作时准确，但并无就其准确性、完整性或及时性作出任何保证，"
            "亦不会就任何错误、遗漏或因依赖本资讯而产生的任何损失承担责任。\n\n"
            "必须注意，投资涉及风险，投资价值及来自投资的收入可能会因市场状况及税务协议而波动，"
            "投资者可能无法取回全部投资本金。过往表现及收益率并非当前及未来结果的可靠指标。\n\n"
            "本内容并非针对任何特定司法管辖区的投资者而提供，不同司法管辖区的投资者应自行确保使用本内容符合当地法例及规定。"
            "本公司保留随时修改、更新或撤回本内容的权利，而毋须事先通知。"
        ),
        "copyright": "© Aurum Infinity Capital Limited  // 版权所有",
    },

    "en": {
        # Header
        "search_placeholder": "Ticker or company name...",
        "search_btn": "Search",
        "lang_label": "Language",

        # Page title
        "terminal_title": "Investment Decision Terminal",

        # Fundamental analysis
        "fundamental_title": "Fundamental Decision Matrix",
        "fundamental_label": "Fundamentals",
        "card_biz":    "Business Model",  "icon_biz":    "Strategy",
        "card_exec":   "Governance",      "icon_exec":   "Management",
        "card_finance":"Financial Quality","icon_finance":"Financials",
        "card_call":   "Earnings Outlook","icon_call":   "Outlook",

        # Technical analysis
        "technical_title": "Technical & Sentiment Diagnostics",
        "technical_label": "Market Dynamics",
        "card_ta_price":   "Price Action",     "icon_ta_price":   "Technical",
        "card_ta_analyst": "Market Forecast",  "icon_ta_analyst": "Analysts",
        "card_ta_social":  "Social Sentiment", "icon_ta_social":  "Sentiment",

        # JS dynamic messages
        "loading_msgs": ["Collecting data...", "Analyzing...", "Almost done!", "Results coming right up!"],
        "confirm_reanalyze": "Re-analyze this section?\n\n⚠️ This will call the AI API to generate a fresh analysis.",
        "updating": "Updating...",
        "updated":  "✅ Updated",
        "no_data":  "No data available",
        "copied":       "Copied to clipboard",
        "copy_manual":  "Please copy manually: ",
        "share_text":   "View {ticker} {title} analysis",
        "cache_label":  "Cached Data",
        "fresh_label":  "AI Live Analysis",
        "init_msg":     "Initializing...",
        "standby_msg":  "Standby...",
        "smart_terminal": "AI Terminal",

        # Popup window button titles
        "btn_minimize": "Minimize",
        "btn_maximize": "Maximize",
        "btn_close":    "Close",
        "btn_scroll_top": "Back to top",
        "btn_share":    "Share",

        # Error page
        "error_title":        "Invalid Ticker Symbol",
        "error_unrecognized": "The system could not recognize ticker",
        "error_hint":         "Please verify the ticker is correct, e.g. AAPL, TSLA, NVDA, 0700.HK",
        "error_search_placeholder": "Enter ticker symbol...",
        "error_back_default": "← Back to default",

        # Disclaimer
        "disclaimer_title": "Disclaimer & Risk Disclosure",
        "disclaimer_body": (
            "This information is for general communication purposes only and is provided for informational and reference purposes. "
            "It is educational in nature and is not intended as advice, recommendation, or solicitation regarding any specific investment "
            "product, strategy, or plan feature, nor does it constitute a commitment by Aureum Infinity Capital Limited to engage in any "
            "transaction described herein. Any examples used are generic, hypothetical, and for illustrative purposes only. "
            "This material does not contain sufficient information to support an investment decision, and you should not rely on it to "
            "evaluate the merits of investing in any securities or products.\n\n"
            "Additionally, you should independently assess the legal, regulatory, tax, credit, and accounting implications of any "
            "investment, and together with your own professional advisors, determine whether any investment described herein is suitable "
            "for your personal objectives. Investors should ensure that they obtain all relevant information available before making "
            "any investment.\n\n"
            "Any forecasts, figures, opinions, investment techniques, and strategies set out in this information are for information "
            "purposes only, based on certain assumptions and current market conditions, and are subject to change without notice. "
            "All information presented has been prepared with care to ensure accuracy at the time of publication, but no warranty is "
            "given as to accuracy, completeness or timeliness, and there should be no reliance on it in connection with any investment "
            "decision.\n\n"
            "It must be noted that investment involves risk. The value of investments and the income from them may fluctuate in "
            "accordance with market conditions and taxation agreements, and investors may not get back the full amount invested. "
            "Past performance and yield are not a reliable indicator of current and future results.\n\n"
            "This content is not directed to investors in any particular jurisdiction. Investors in different jurisdictions should "
            "ensure that their use of this content complies with local laws and regulations. The Company reserves the right to modify, "
            "update or withdraw this content at any time without notice."
        ),
        "copyright": "© Aurum Infinity Capital Limited  // All Rights Reserved",
    },
}

SUPPORTED_LANGS = list(TRANSLATIONS.keys())
DEFAULT_LANG = "zh_hk"


def get_translations(lang: str) -> dict:
    """取得指定語言的翻譯字典，找不到時 fallback 到繁中"""
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
