"""
Moebius 极繁主义主题 CSS — 暖赭石色调 / 装饰边框 / 星空元素 / 手绘质感
"""
MOEBIUS_CSS = """
<style>
/* ═══════════════ 全局基底 ═══════════════ */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');

#root, .main, .stApp {
    background: linear-gradient(175deg, #F5F0E8 0%, #EDE4D4 30%, #F2E8DC 60%, #F5F0E8 100%) !important;
    font-family: 'Noto Serif SC', 'Georgia', '宋体', serif !important;
}

/* 微妙的星空粒子背景（Moebius 标志性的星空沙漠） */
.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 0;
    background:
        radial-gradient(1px 1px at 10% 15%, rgba(212, 168, 67, 0.3), transparent),
        radial-gradient(1px 1px at 25% 35%, rgba(212, 168, 67, 0.2), transparent),
        radial-gradient(1px 1px at 40% 10%, rgba(184, 123, 107, 0.25), transparent),
        radial-gradient(1px 1px at 55% 25%, rgba(196, 149, 106, 0.3), transparent),
        radial-gradient(1px 1px at 70% 40%, rgba(212, 168, 67, 0.2), transparent),
        radial-gradient(1px 1px at 85% 20%, rgba(184, 123, 107, 0.25), transparent),
        radial-gradient(2px 2px at 15% 50%, rgba(42, 59, 76, 0.15), transparent),
        radial-gradient(2px 2px at 60% 55%, rgba(42, 59, 76, 0.12), transparent),
        radial-gradient(1px 1px at 80% 45%, rgba(212, 168, 67, 0.2), transparent),
        radial-gradient(1px 1px at 5% 70%, rgba(196, 149, 106, 0.2), transparent),
        radial-gradient(1px 1px at 35% 65%, rgba(184, 123, 107, 0.2), transparent),
        radial-gradient(1.5px 1.5px at 90% 60%, rgba(212, 168, 67, 0.25), transparent);
}

/* ═══════════════ 侧边栏：深靛蓝梦境 ═══════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E2D3D 0%, #253545 30%, #1A2835 100%) !important;
    border-right: 3px double #C4956A !important;
    box-shadow: 4px 0 20px rgba(0,0,0,0.3) !important;
}
[data-testid="stSidebar"] * {
    color: #E8DCC8 !important;
}
[data-testid="stSidebar"] h1 {
    font-family: 'Noto Serif SC', serif !important;
    font-weight: 700 !important;
    color: #D4A843 !important;
    letter-spacing: 2px;
    text-shadow: 0 2px 8px rgba(212, 168, 67, 0.3);
    border-bottom: 2px solid rgba(196, 149, 106, 0.4);
    padding-bottom: 12px;
    margin-bottom: 16px;
}
[data-testid="stSidebar"] hr, [data-testid="stSidebar"] .stMarkdown hr {
    border-color: rgba(196, 149, 106, 0.3) !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #D4C5B0 !important;
    font-size: 15px !important;
    transition: color 0.3s;
}
[data-testid="stSidebar"] .stRadio label:hover {
    color: #D4A843 !important;
}
[data-testid="stSidebar"] button {
    background: linear-gradient(135deg, #3D2E1E, #5C4033) !important;
    border: 1px solid #8B7355 !important;
    color: #E8DCC8 !important;
    border-radius: 3px !important;
    font-family: 'Noto Serif SC', serif !important;
    letter-spacing: 1px;
}
[data-testid="stSidebar"] button:hover {
    background: linear-gradient(135deg, #5C4033, #7B5B3A) !important;
    border-color: #D4A843 !important;
}

/* ═══════════════ 页面标题 ═══════════════ */
h1 {
    font-family: 'Noto Serif SC', 'Georgia', serif !important;
    font-weight: 700 !important;
    color: #2A3B4C !important;
    letter-spacing: 3px !important;
    text-align: center;
    position: relative;
}
h1::after {
    content: '✦ ✧ ✦';
    display: block;
    text-align: center;
    font-size: 18px;
    color: #D4A843;
    letter-spacing: 8px;
    margin-top: 8px;
}
h2 {
    font-family: 'Noto Serif SC', serif !important;
    font-weight: 600 !important;
    color: #3D2E1E !important;
    border-left: 4px solid #C4956A;
    padding-left: 12px;
    margin-top: 20px;
}
h3 {
    font-family: 'Noto Serif SC', serif !important;
    font-weight: 600 !important;
    color: #5C4033 !important;
}

/* ═══════════════ 知识卡片 — Moebius 装饰框 ═══════════════ */
.moebius-card {
    background: linear-gradient(160deg, #FDFAF4 0%, #F5EDDE 50%, #FDFAF4 100%) !important;
    border: 2px solid #C4956A !important;
    border-radius: 6px !important;
    padding: 24px 28px !important;
    margin: 18px 0 !important;
    position: relative !important;
    box-shadow:
        0 4px 16px rgba(42, 59, 76, 0.12),
        inset 0 0 60px rgba(196, 149, 106, 0.04) !important;
}

/* 装饰性内框 */
.moebius-card::before {
    content: '';
    position: absolute;
    top: 6px; left: 6px; right: 6px; bottom: 6px;
    border: 1px solid rgba(212, 168, 67, 0.3);
    border-radius: 4px;
    pointer-events: none;
}

/* 四角星形装饰 */
.moebius-card::after {
    content: '✦';
    position: absolute;
    top: -10px; right: 16px;
    font-size: 20px;
    color: #D4A843;
    text-shadow: 0 0 8px rgba(212, 168, 67, 0.4);
    pointer-events: none;
}

.moebius-card .card-number {
    font-family: 'Georgia', serif;
    font-size: 13px;
    color: #8B7355;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 1px dashed rgba(196, 149, 106, 0.4);
    padding-bottom: 8px;
    margin-bottom: 14px;
}
.moebius-card .card-domain {
    display: inline-block;
    background: linear-gradient(135deg, #F0E6D3, #E8D8C0);
    border: 1px solid #C4956A;
    border-radius: 2px;
    padding: 3px 14px;
    font-size: 12px;
    color: #5C4033;
    letter-spacing: 2px;
    margin-bottom: 10px;
}
.moebius-card .card-title {
    font-family: 'Noto Serif SC', serif;
    font-size: 20px;
    font-weight: 700;
    color: #2A3B4C;
    margin: 8px 0 12px 0;
    letter-spacing: 1px;
}
.moebius-card .card-content {
    font-family: 'Noto Serif SC', serif;
    font-size: 15px;
    color: #3D3028;
    line-height: 1.9;
    text-align: justify;
    padding-left: 12px;
    border-left: 2px solid rgba(196, 149, 106, 0.3);
}
.moebius-card .card-divider {
    text-align: center;
    color: #D4A843;
    letter-spacing: 6px;
    margin: 10px 0;
    font-size: 10px;
}

/* ═══════════════ 测验题目框 ═══════════════ */
div[data-testid="stExpander"] {
    background: linear-gradient(160deg, #FDFAF4 0%, #F5EDDE 100%) !important;
    border: 1px solid #D4C5B0 !important;
    border-radius: 4px !important;
    margin: 8px 0 !important;
}
div[data-testid="stExpander"]:hover {
    border-color: #C4956A !important;
    box-shadow: 0 2px 12px rgba(196, 149, 106, 0.15) !important;
}

/* ═══════════════ 按钮 ═══════════════ */
.stButton > button {
    background: linear-gradient(135deg, #8B7355, #6B5B45) !important;
    border: 2px solid #A08060 !important;
    color: #F5F0E8 !important;
    font-family: 'Noto Serif SC', serif !important;
    font-weight: 600 !important;
    letter-spacing: 2px !important;
    border-radius: 3px !important;
    padding: 8px 24px !important;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(42, 59, 76, 0.2);
}
.stButton > button:hover {
    background: linear-gradient(135deg, #A08060, #8B7355) !important;
    border-color: #D4A843 !important;
    box-shadow: 0 4px 16px rgba(196, 149, 106, 0.3);
    transform: translateY(-1px);
}

/* 提交按钮特殊处理 */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #5C4033, #7B5B3A) !important;
    border: 2px solid #D4A843 !important;
    color: #F5F0E8 !important;
    letter-spacing: 3px !important;
}

/* ═══════════════ 选择框 / 下拉 ═══════════════ */
div[data-baseweb="select"] > div {
    background: #FDFAF4 !important;
    border: 1px solid #C4956A !important;
    border-radius: 3px !important;
    font-family: 'Noto Serif SC', serif !important;
}

/* ═══════════════ 滑块 ═══════════════ */
div[data-testid="stSlider"] > div {
    accent-color: #C4956A;
}

/* ═══════════════ Metric 指标卡 ═══════════════ */
div[data-testid="stMetric"] {
    background: linear-gradient(160deg, #FDFAF4, #F5EDDE) !important;
    border: 1px solid #D4C5B0 !important;
    border-radius: 4px !important;
    padding: 12px !important;
    box-shadow: 0 2px 10px rgba(42, 59, 76, 0.08);
}
div[data-testid="stMetric"] label {
    color: #8B7355 !important;
    font-family: 'Noto Serif SC', serif !important;
    letter-spacing: 2px;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-family: 'Georgia', serif !important;
    color: #2A3B4C !important;
}

/* ═══════════════ 表格 ═══════════════ */
div[data-testid="stTable"], .stDataFrame {
    border: 1px solid #D4C5B0 !important;
    border-radius: 3px;
}
thead tr th {
    background: linear-gradient(180deg, #3D2E1E, #5C4033) !important;
    color: #E8DCC8 !important;
    font-family: 'Noto Serif SC', serif !important;
    font-weight: 600 !important;
    letter-spacing: 2px !important;
}
tbody tr:nth-child(even) {
    background: rgba(196, 149, 106, 0.06) !important;
}
tbody tr:nth-child(odd) {
    background: #FDFAF4 !important;
}

/* ═══════════════ 提示框 / 成功/错误信息 ═══════════════ */
div[data-testid="stSuccess"] {
    background: linear-gradient(135deg, #E8E0CF, #F0EBE0) !important;
    border-left: 4px solid #8FA88C !important;
    color: #3D3028 !important;
}
div[data-testid="stError"] {
    background: linear-gradient(135deg, #F5E8DC, #F0DFD0) !important;
    border-left: 4px solid #B87B6B !important;
    color: #3D3028 !important;
}
div[data-testid="stInfo"] {
    background: linear-gradient(135deg, #EDE4D4, #F2E8DC) !important;
    border-left: 4px solid #C4956A !important;
    color: #3D3028 !important;
}

/* ═══════════════ Spinbox ═══════════════ */
div[data-testid="stSpinner"] {
    color: #D4A843 !important;
}

/* ═══════════════ Radio 美化 ═══════════════ */
.stRadio [role="radiogroup"] label {
    font-family: 'Noto Serif SC', serif !important;
    color: #3D3028 !important;
    padding: 6px 12px;
    border-radius: 2px;
    transition: background 0.2s;
}
.stRadio [role="radiogroup"] label:hover {
    background: rgba(196, 149, 106, 0.08);
}

/* ═══════════════ 装饰性水平线 ═══════════════ */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg,
        transparent, #D4C5B0 20%, #C4956A 50%, #D4C5B0 80%, transparent
    ) !important;
    margin: 20px 0 !important;
}

/* ═══════════════ 滚动条 ═══════════════ */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #F5F0E8; }
::-webkit-scrollbar-thumb {
    background: #C4956A;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover { background: #8B7355; }
</style>
"""
