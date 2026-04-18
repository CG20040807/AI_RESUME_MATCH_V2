import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


import sys
import os
import re
import io
import json
from pathlib import Path
from datetime import datetime

# ── 路径修复（必须最先，且只保留这一份）──
# 当前文件位于 /app/main.py
# 所以项目根目录是 parents[1]
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

import streamlit as st

# ── 页面配置（必须是第一个 st 命令）──
st.set_page_config(
    page_title="AI 智能简历评估系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 项目模块 ──
from core.analyzer import analyze
from core.scorer import extract_score
from core.ranker import rank_candidates
from core.summarizer import summarize
from utils.file_parser import parse_docx
from utils.text_cleaner import clean_text
from utils.docx_exporter import export_to_docx, export_single_to_docx

# ══════════════════════════════════════════════════════
#  全局样式
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp { background: #f0f4f8; }

/* 顶部横幅 */
.hero {
    background: linear-gradient(135deg,#1e3a5f 0%,#2563eb 55%,#7c3aed 100%);
    border-radius:16px; padding:36px 40px; margin-bottom:28px;
    color:white; position:relative; overflow:hidden;
}
.hero-badge {
    display:inline-block; background:rgba(255,255,255,0.18);
    border:1px solid rgba(255,255,255,0.3); border-radius:20px;
    padding:3px 14px; font-size:0.75rem; margin-bottom:10px;
}
.hero-title { font-size:2.2rem; font-weight:800; margin:0 0 6px; }
.hero-sub   { font-size:1rem; opacity:0.85; margin:0; }

/* 白卡片 */
.card {
    background:white; border-radius:14px; padding:24px;
    box-shadow:0 1px 4px rgba(0,0,0,0.06),0 4px 16px rgba(0,0,0,0.03);
    margin-bottom:16px; border:1px solid #e8edf2;
}
.card-title {
    font-size:0.75rem; font-weight:600; text-transform:uppercase;
    letter-spacing:0.08em; color:#6b7280; margin-bottom:16px;
}

/* 排名卡片 */
.rank-card {
    background:white; border-radius:12px; padding:16px 20px;
    margin-bottom:10px; border:1.5px solid #e8edf2;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
    display:flex; align-items:center; gap:12px;
}
.rank-below { border-color:#fca5a5 !important; background:#fff5f5 !important; }

/* 指标卡 */
.metric-card {
    background:white; border-radius:12px; padding:20px;
    text-align:center; border:1px solid #e8edf2;
    box-shadow:0 1px 4px rgba(0,0,0,0.04);
}
.metric-icon  { font-size:1.4rem; margin-bottom:6px; }
.metric-val   { font-size:1.8rem; font-weight:800; color:#1e293b; line-height:1.2; }
.metric-label { font-size:0.78rem; color:#6b7280; margin-top:4px; }

/* 评分条 */
.sbar-wrap  { margin:5px 0; }
.sbar-label { font-size:0.8rem; color:#475569; margin-bottom:3px; display:flex; justify-content:space-between; }
.sbar-bg    { background:#f1f5f9; border-radius:6px; height:10px; overflow:hidden; }
.sbar-fill  { height:100%; border-radius:6px; }

/* 推荐标签 */
.badge { display:inline-block; border-radius:20px; padding:3px 12px; font-size:0.75rem; font-weight:600; }
.b-green  { background:#dcfce7; color:#15803d; }
.b-blue   { background:#dbeafe; color:#1d4ed8; }
.b-yellow { background:#fef9c3; color:#854d0e; }
.b-red    { background:#fee2e2; color:#b91c1c; }
.b-gray   { background:#f1f5f9; color:#475569; }

/* 状态行 */
.sitem { padding:10px 16px; border-radius:8px; margin:4px 0; font-size:0.88rem; }
.srun  { background:#eff6ff; border-left:3px solid #3b82f6; color:#1e40af; }
.sdone { background:#f0fdf4; border-left:3px solid #22c55e; color:#15803d; }
.serr  { background:#fef2f2; border-left:3px solid #ef4444; color:#991b1b; }

/* 对比表 */
.ctable { width:100%; border-collapse:collapse; font-size:0.87rem; }
.ctable th { background:#1e3a5f; color:white; padding:10px 14px; text-align:left; font-weight:600; }
.ctable td { padding:10px 14px; border-bottom:1px solid #e8edf2; }
.ctable tr:nth-child(even) td { background:#f8fafc; }

/* 侧边栏深色 */
[data-testid="stSidebar"] { background:#1e293b !important; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stSidebar"] .stMarkdown h3 { color:#93c5fd !important; }

/* 按钮悬停 */
.stButton > button { border-radius:10px !important; font-weight:600 !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════
def score_hex(s):
    if s >= 80:
        return "#16a34a"
    if s >= 65:
        return "#2563eb"
    if s >= 50:
        return "#d97706"
    return "#dc2626"

def rec_badge_html(rec):
    m = {
        "强烈推荐": ("b-green", "⭐ 强烈推荐"),
        "推荐": ("b-blue", "✅ 推荐"),
        "观察": ("b-yellow", "👀 观察"),
        "不推荐": ("b-red", "❌ 不推荐"),
    }
    cls, label = m.get(rec, ("b-gray", "— " + str(rec)))
    return '<span class="badge ' + cls + '">' + label + '</span>'

def score_bar_html(label, val, max_val=100):
    pct = min(100, max(0, int(val / max_val * 100)))
    color = score_hex(val)
    return (
        '<div class="sbar-wrap">'
        '<div class="sbar-label"><span>' + label + '</span>'
        '<span><b>' + str(val) + '</b>/' + str(max_val) + '</span></div>'
        '<div class="sbar-bg"><div class="sbar-fill" style="width:' + str(pct) + '%;background:' + color + '"></div></div>'
        '</div>'
    )

def extract_sub_scores(text):
    keys = ["技能匹配", "经验匹配", "教育背景", "综合潜力", "表达沟通"]
    out = {}
    for k in keys:
        m = re.search(k + r"[:：]\s*(\d+)", text)
        out[k] = int(m.group(1)) if m else None
    return out

def log_cls(log_line):
    return "sdone" if log_line.startswith("✅") else "serr"


# ══════════════════════════════════════════════════════
#  Session State
# ══════════════════════════════════════════════════════
DEFAULTS = {
    "results": [],
    "summary": "",
    "word_bytes": None,
    "job_title_cache": "",
    "jd_cache": "",
    "criteria_cache": "",
    "logs": [],
    "expanded_all": False,
}

for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ══════════════════════════════════════════════════════
#  侧边栏
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🧠 AI 简历评估系统")
    st.markdown("---")

    st.markdown("### ⚙️ 筛选与排序")
    score_threshold = st.slider("最低分数门槛", 0, 100, 0, 5, help="低于此分候选人标红显示")
    all_recs = ["强烈推荐", "推荐", "观察", "不推荐", "未提取", "无法评估"]
    rec_filter = st.multiselect("推荐等级筛选", all_recs, default=all_recs)
    sort_by = st.radio("排序方式", ["综合评分（高→低）", "综合评分（低→高）", "文件名"], index=0)

    st.markdown("---")
    st.markdown("### 📊 当前数据")

    if st.session_state.results:
        _r = st.session_state.results
        _n = len(_r)
        _avg = sum(x["score"] for x in _r) / _n if _n else 0
        _pass = sum(1 for x in _r if x["score"] >= score_threshold)
        _rec = sum(1 for x in _r if x.get("recommendation") in ("强烈推荐", "推荐"))

        st.markdown(
            '<div style="color:#94a3b8;font-size:0.82rem;line-height:2.4">'
            '👥 候选人：<b style="color:white">' + str(_n) + '</b><br>'
            '✅ 达标：<b style="color:#4ade80">' + str(_pass) + '</b><br>'
            '📈 均分：<b style="color:white">' + f"{_avg:.1f}" + '</b><br>'
            '⭐ 推荐：<b style="color:#fbbf24">' + str(_rec) + ' 人</b>'
            '</div>',
            unsafe_allow_html=True
        )
        st.markdown("")
        if st.button("🗑️ 清空所有结果", use_container_width=True):
            st.session_state.results = []
            st.session_state.summary = ""
            st.session_state.word_bytes = None
            st.session_state.logs = []
            st.rerun()
    else:
        st.markdown('<div style="color:#64748b;font-size:0.82rem">暂无结果</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ❓ 使用说明")
    st.markdown(
        '<div style="font-size:0.79rem;color:#94a3b8;line-height:2.2">'
        '1️⃣ 填写岗位名称<br>2️⃣ 粘贴岗位JD<br>3️⃣ 填写评估标准<br>'
        '4️⃣ 上传 .docx 简历<br>5️⃣ 点击「开始分析」<br>6️⃣ 查看结果并导出</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown(
        '<div style="color:#475569;font-size:0.7rem;text-align:center">'
        'AI Resume Assessment v2<br>Qwen · DeepSeek · Multi-Model</div>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════
#  顶部横幅
# ══════════════════════════════════════════════════════
st.markdown(
    '<div class="hero">'
    '<div class="hero-badge">🤖 AI Powered · Multi-Model Fallback · v2.0</div>'
    '<div class="hero-title">🧠 AI 智能简历评估系统</div>'
    '<div class="hero-sub">批量简历分析 · 多维评分排名 · 候选人对比 · Word / CSV / JSON 导出</div>'
    '</div>',
    unsafe_allow_html=True
)


# ══════════════════════════════════════════════════════
#  输入区
# ══════════════════════════════════════════════════════
st.markdown('<div class="card"><div class="card-title">📋 岗位信息 &amp; 简历上传</div>', unsafe_allow_html=True)

col_l, col_m, col_r = st.columns([1.2, 1.2, 1])

with col_l:
    job_title = st.text_input(
        "📌 岗位名称 *",
        value=st.session_state.job_title_cache,
        placeholder="例：产品经理实习生 / 数据分析师"
    )
    jd = st.text_area(
        "📄 岗位JD *",
        value=st.session_state.jd_cache,
        height=180,
        placeholder="粘贴招聘JD，越详细分析越准确..."
    )

with col_m:
    criteria = st.text_area(
        "📐 评估标准 *",
        value=st.session_state.criteria_cache,
        height=120,
        placeholder="例：优先有产品实习、熟悉SQL、逻辑表达强..."
    )
    extra_notes = st.text_area(
        "📝 补充备注（可选）",
        height=88,
        placeholder="其他要求，如：不考虑跨专业候选人..."
    )

with col_r:
    uploaded_files = st.file_uploader(
        "📂 上传简历（.docx，支持批量）",
        type=["docx"],
        accept_multiple_files=True,
        help="仅支持 Word .docx 格式"
    )
    if uploaded_files:
        file_list_html = "".join(
            '<div style="font-size:0.8rem;color:#3b82f6;padding:2px 0">📄 ' + f.name + '</div>'
            for f in uploaded_files
        )
        st.markdown(
            '<div style="background:#eff6ff;border-radius:10px;padding:12px 16px;margin-top:8px">'
            '<div style="color:#1d4ed8;font-weight:600;margin-bottom:6px">📂 已上传 '
            + str(len(uploaded_files)) + ' 份简历</div>' +
            file_list_html + '</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background:#f8fafc;border:2px dashed #cbd5e1;border-radius:10px;'
            'padding:30px;text-align:center;margin-top:8px;color:#94a3b8">'
            '<div style="font-size:2rem">📁</div>'
            '<div style="font-size:0.85rem;margin-top:6px">拖拽文件或点击上传</div></div>',
            unsafe_allow_html=True
        )

st.markdown('</div>', unsafe_allow_html=True)


# ── 按钮行 ──
b1, b2, b3, b4 = st.columns([2, 1, 1, 1])
with b1:
    start_btn = st.button("🚀 开始分析", use_container_width=True, type="primary")
with b2:
    clear_btn = st.button("🔄 清空输入", use_container_width=True)
with b3:
    demo_btn = st.button("💡 填入示例", use_container_width=True)
with b4:
    help_btn = st.button("📖 使用说明", use_container_width=True)

if clear_btn:
    st.session_state.job_title_cache = ""
    st.session_state.jd_cache = ""
    st.session_state.criteria_cache = ""
    st.rerun()

if demo_btn:
    st.session_state.job_title_cache = "AI产品经理实习生"
    st.session_state.jd_cache = (
        "负责AI产品从0到1的设计与迭代，包括需求分析、PRD撰写、"
        "与技术团队协作推进落地，跟进产品数据并持续优化用户体验。"
    )
    st.session_state.criteria_cache = (
        "优先有产品实习经验；熟悉AI工具使用；具备数据分析能力；"
        "逻辑表达清晰；大数据、计算机专业背景加分。"
    )
    st.rerun()

if help_btn:
    with st.expander("📖 使用说明", expanded=True):
        st.markdown("""
**① 填写岗位信息** — JD和评估标准越详细，AI分析越准确。

**② 上传简历** — 支持批量 `.docx`，每份对应一位候选人。

**③ 开始分析** — 实时进度显示，完成后自动排名。

**④ 查看结果** — 排名总览 · 逐人详情（含分数条）· 候选人对比 · 综合总结。

**⑤ 多种导出** — Word完整报告 · 单人报告 · JSON数据 · CSV排名表。

💡 侧边栏可按分数门槛和推荐等级筛选候选人。
        """)


# ══════════════════════════════════════════════════════
#  主分析流程
# ══════════════════════════════════════════════════════
if start_btn:
    errors = []
    if not job_title.strip():
        errors.append("请填写岗位名称")
    if not jd.strip():
        errors.append("请填写岗位JD")
    if not criteria.strip():
        errors.append("请填写评估标准")
    if not uploaded_files:
        errors.append("请上传至少一份简历")

    if errors:
        for e in errors:
            st.error("⚠️ " + e)
        st.stop()

    # 缓存输入
    st.session_state.job_title_cache = job_title
    st.session_state.jd_cache = jd
    st.session_state.criteria_cache = criteria

    full_criteria = criteria
    if extra_notes.strip():
        full_criteria = criteria + "\n\n补充要求：" + extra_notes.strip()

    results = []
    total = len(uploaded_files)
    logs = []

    st.markdown("---")
    st.markdown("### ⏳ 分析进行中...")
    prog_bar = st.progress(0)
    status_ph = st.empty()
    log_ph = st.empty()

    for i, file in enumerate(uploaded_files):
        name = file.name.replace(".docx", "")
        status_ph.markdown(
            '<div class="sitem srun">🔄 <b>正在分析（'
            + str(i + 1) + '/' + str(total) + '）：' + name + '</b></div>',
            unsafe_allow_html=True
        )

        raw = parse_docx(file)

        if not raw or str(raw).startswith("【"):
            entry = {
                "name": name,
                "analysis": "⚠️ 简历解析失败：" + str(raw),
                "score": 0,
                "recommendation": "无法评估",
                "sub_scores": {}
            }
            logs.append("❌ " + name + " — 解析失败")
        else:
            text = clean_text(raw)
            try:
                analysis = analyze(job_title, jd, full_criteria, text)
            except Exception as exc:
                analysis = "AI分析异常：" + str(exc)

            score = extract_score(analysis)
            rec = "未提取"
            m = re.search(r"推荐建议[:：]\s*(强烈推荐|推荐|观察|不推荐)", analysis)
            if m:
                rec = m.group(1).strip()

            entry = {
                "name": name,
                "analysis": analysis,
                "score": score,
                "recommendation": rec,
                "sub_scores": extract_sub_scores(analysis)
            }
            logs.append("✅ " + name + " — " + str(score) + "分 · " + rec)

        results.append(entry)
        prog_bar.progress((i + 1) / total)

        log_html = "".join(
            '<div class="sitem ' + log_cls(l) + '">' + l + '</div>'
            for l in logs
        )
        log_ph.markdown(log_html, unsafe_allow_html=True)

    status_ph.markdown(
        '<div class="sitem sdone">✅ <b>所有简历分析完成，正在生成总结...</b></div>',
        unsafe_allow_html=True
    )

    ranked = rank_candidates(results)

    try:
        summary = summarize(job_title, jd, full_criteria, ranked)
    except Exception as exc:
        summary = "总结生成失败：" + str(exc)

    try:
        word_bytes = export_to_docx(job_title, jd, full_criteria, ranked, summary)
    except Exception:
        word_bytes = None

    st.session_state.results = ranked
    st.session_state.summary = summary
    st.session_state.word_bytes = word_bytes
    st.session_state.logs = logs

    prog_bar.empty()
    status_ph.empty()
    log_ph.empty()
    st.success("🎉 分析完成！共处理 " + str(total) + " 份简历")
    st.rerun()


# ══════════════════════════════════════════════════════
#  结果展示
# ══════════════════════════════════════════════════════
if st.session_state.results:
    raw_ranked = st.session_state.results
    summary = st.session_state.summary
    job_cache = st.session_state.job_title_cache

    # ── 排序 ──
    if sort_by == "综合评分（高→低）":
        disp = sorted(raw_ranked, key=lambda x: x["score"], reverse=True)
    elif sort_by == "综合评分（低→高）":
        disp = sorted(raw_ranked, key=lambda x: x["score"])
    else:
        disp = sorted(raw_ranked, key=lambda x: x["name"])

    # ── 推荐等级筛选 ──
    disp = [r for r in disp if r.get("recommendation", "未提取") in rec_filter]

    # ── 指标卡 ──
    st.markdown("---")
    st.markdown("## 📊 评估结果  ·  " + job_cache)

    _n = len(raw_ranked)
    _avg = sum(r["score"] for r in raw_ranked) / _n if _n else 0
    _pass = sum(1 for r in raw_ranked if r["score"] >= score_threshold)
    _rec = sum(1 for r in raw_ranked if r.get("recommendation") in ("强烈推荐", "推荐"))
    top1 = raw_ranked[0] if raw_ranked else {}

    mc = st.columns(5)
    for col, icon, val, label in [
        (mc[0], "🥇", top1.get("name", "—"), "最佳候选人"),
        (mc[1], "🎯", str(top1.get("score", 0)) + " 分", "最高分"),
        (mc[2], "📈", f"{_avg:.1f} 分", "平均分"),
        (mc[3], "👥", str(_pass) + "/" + str(_n), "达标（≥" + str(score_threshold) + "分）"),
        (mc[4], "⭐", str(_rec) + " 人", "推荐人数"),
    ]:
        col.markdown(
            '<div class="metric-card">'
            '<div class="metric-icon">' + icon + '</div>'
            '<div class="metric-val">' + str(val) + '</div>'
            '<div class="metric-label">' + label + '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # ── 分布图 ──
    st.markdown("")
    with st.expander("📊 分数分布图", expanded=True):
        chart_data = {r["name"][:12]: r["score"] for r in raw_ranked}
        st.bar_chart(chart_data, height=220)

    # ── 工具栏 ──
    st.markdown("")
    tb = st.columns([2, 1, 1, 1, 1])
    with tb[0]:
        kw = st.text_input("🔍 搜索候选人", placeholder="输入姓名筛选...", label_visibility="collapsed")
        if kw:
            disp = [r for r in disp if kw.lower() in r["name"].lower()]
    with tb[1]:
        if st.button("📂 全部展开", use_container_width=True):
            st.session_state.expanded_all = True
    with tb[2]:
        if st.button("📁 全部收起", use_container_width=True):
            st.session_state.expanded_all = False
    with tb[3]:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    with tb[4]:
        st.markdown(
            '<div style="text-align:right;color:#6b7280;font-size:0.8rem;padding-top:8px">'
            '显示 ' + str(len(disp)) + '/' + str(_n) + '</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ══════ 四个 Tab ══════
    tab1, tab2, tab3, tab4 = st.tabs(["🏅 排名总览", "🔍 逐人详情", "📊 候选人对比", "📋 综合总结"])

    # ── Tab1：排名总览 ──
    with tab1:
        if not disp:
            st.info("暂无符合筛选条件的候选人")
        for i, r in enumerate(disp):
            sc = r["score"]
            color = score_hex(sc)
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "#" + str(i + 1)
            badge = rec_badge_html(r.get("recommendation", "未提取"))
            below = sc < score_threshold
            extra_cls = " rank-below" if below else ""
            warn_html = (
                '<span style="color:#ef4444;font-size:0.75rem;margin-left:8px">⚠️低于门槛</span>'
                if below else ""
            )
            st.markdown(
                '<div class="rank-card' + extra_cls + '">'
                '<span style="font-size:1.3rem;min-width:40px">' + medal + '</span>'
                '<span style="font-weight:600;font-size:1rem;color:#1e293b;flex:1">' + r["name"] + '</span>'
                + badge +
                '<span style="font-size:1.3rem;font-weight:800;color:' + color + ';margin-left:12px">'
                + str(sc) +
                '<span style="font-size:0.7rem;color:#94a3b8">/100</span></span>'
                + warn_html +
                '</div>',
                unsafe_allow_html=True
            )

    # ── Tab2：逐人详情 ──
    with tab2:
        if not disp:
            st.info("暂无符合筛选条件的候选人")
        for i, r in enumerate(disp):
            sc = r["score"]
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "#" + str(i + 1)
            rec = r.get("recommendation", "未提取")
            exp = st.session_state.expanded_all or (i == 0)

            with st.expander(medal + "  " + r["name"] + "  ·  " + str(sc) + "分  ·  " + rec, expanded=exp):
                left, right = st.columns([1, 1.6])

                with left:
                    bars_html = score_bar_html("综合总分", sc)
                    sub = r.get("sub_scores", {})
                    for sk, sv in sub.items():
                        if sv is not None:
                            bars_html += score_bar_html(sk, sv)

                    st.markdown(
                        '<div style="background:#f8fafc;border-radius:10px;padding:16px">'
                        '<div style="font-size:0.75rem;font-weight:600;color:#6b7280;'
                        'text-transform:uppercase;margin-bottom:12px">评分详情</div>'
                        + bars_html +
                        '<div style="margin-top:14px;padding-top:12px;border-top:1px solid #e8edf2">'
                        + rec_badge_html(rec) +
                        '</div></div>',
                        unsafe_allow_html=True
                    )

                    try:
                        sb = export_single_to_docx(
                            job_cache,
                            st.session_state.jd_cache,
                            st.session_state.criteria_cache,
                            r
                        )
                        st.download_button(
                            "📥 导出 " + r["name"] + " 报告",
                            data=sb,
                            file_name=r["name"] + "_评估报告.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key="sdl_" + str(i)
                        )
                    except Exception:
                        pass

                with right:
                    st.markdown("**📝 AI 分析内容**")
                    st.markdown(r["analysis"])

    # ── Tab3：候选人对比 ──
    with tab3:
        if len(disp) < 2:
            st.info("至少需要 2 位候选人才能进行对比")
        else:
            all_names = [r["name"] for r in disp]
            default_sel = all_names[:min(4, len(all_names))]
            sel_names = st.multiselect(
                "选择要对比的候选人（最多5人）",
                all_names,
                default=default_sel
            )
            clist = [r for r in disp if r["name"] in sel_names][:5]

            if len(clist) >= 2:
                hdr = "<tr><th>维度</th>" + "".join(
                    "<th>" + r["name"] + "</th>" for r in clist
                ) + "</tr>"

                def sc_cell(r, key=None):
                    v = r["score"] if key is None else r.get("sub_scores", {}).get(key)
                    if v is None:
                        return "—"
                    c = score_hex(v)
                    return '<span style="font-weight:700;color:' + c + '">' + str(v) + '</span>'

                dim_rows = ""
                dim_rows += "<tr><td><b>推荐意见</b></td>"
                for r in clist:
                    dim_rows += "<td>" + r.get("recommendation", "—") + "</td>"
                dim_rows += "</tr>"

                dim_rows += "<tr><td><b>综合总分</b></td>"
                for r in clist:
                    dim_rows += "<td>" + sc_cell(r) + "</td>"
                dim_rows += "</tr>"

                for dim in ["技能匹配", "经验匹配", "教育背景", "综合潜力", "表达沟通"]:
                    dim_rows += "<tr><td><b>" + dim + "</b></td>"
                    for r in clist:
                        dim_rows += "<td>" + sc_cell(r, dim) + "</td>"
                    dim_rows += "</tr>"

                st.markdown(
                    '<table class="ctable"><thead>' + hdr +
                    '</thead><tbody>' + dim_rows + '</tbody></table>',
                    unsafe_allow_html=True
                )
                st.markdown("")
                st.markdown("**📊 分数对比图**")
                chart_cmp = {r["name"][:12]: r["score"] for r in clist}
                st.bar_chart(chart_cmp, height=200)

    # ── Tab4：综合总结 ──
    with tab4:
        if summary:
            st.markdown(summary)
        else:
            st.info("暂无总结内容")

        if st.button("🔄 重新生成总结", key="regen_summary"):
            with st.spinner("重新生成中..."):
                try:
                    new_sum = summarize(
                        job_cache,
                        st.session_state.jd_cache,
                        st.session_state.criteria_cache,
                        raw_ranked
                    )
                    st.session_state.summary = new_sum
                    st.rerun()
                except Exception as exc:
                    st.error("生成失败：" + str(exc))

    # ── 导出区 ──
    st.markdown("---")
    st.markdown("### 📥 报告导出")

    exp_cols = st.columns(3)

    with exp_cols[0]:
        if st.session_state.word_bytes:
            ts = datetime.now().strftime("%m%d_%H%M")
            st.download_button(
                "📄 完整评估报告（Word）",
                data=st.session_state.word_bytes,
                file_name=job_cache + "_完整报告_" + ts + ".docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        else:
            st.button("📄 Word报告（生成中...）", disabled=True, use_container_width=True)

    with exp_cols[1]:
        json_rows = []
        for r in raw_ranked:
            json_rows.append({
                "name": r["name"],
                "score": r["score"],
                "recommendation": r.get("recommendation", "未提取"),
                "sub_scores": r.get("sub_scores", {}),
            })
        json_str = json.dumps(json_rows, ensure_ascii=False, indent=2)
        st.download_button(
            "📊 评分数据（JSON）",
            data=json_str.encode("utf-8"),
            file_name=job_cache + "_评分数据.json",
            mime="application/json",
            use_container_width=True
        )

    with exp_cols[2]:
        csv_lines = ["排名,姓名,总分,推荐意见"]
        for i, r in enumerate(raw_ranked, 1):
            csv_lines.append(
                str(i) + "," + r["name"] + "," +
                str(r["score"]) + "," + r.get("recommendation", "未提取")
            )
        csv_str = "\n".join(csv_lines)
        st.download_button(
            "📋 排名表（CSV）",
            data=csv_str.encode("utf-8-sig"),
            file_name=job_cache + "_排名表.csv",
            mime="text/csv",
            use_container_width=True
        )

    # ── 分析日志 ──
    if st.session_state.logs:
        with st.expander("📜 分析日志", expanded=False):
            for log in st.session_state.logs:
                c = "#15803d" if log.startswith("✅") else "#991b1b"
                st.markdown(
                    '<div style="font-size:0.83rem;color:' + c + ';padding:3px 0">' +
                    log + '</div>',
                    unsafe_allow_html=True
                )

else:
    st.markdown(
        '<div style="text-align:center;padding:80px 0;color:#94a3b8">'
        '<div style="font-size:4rem">📋</div>'
        '<div style="font-size:1.3rem;font-weight:600;margin:16px 0 8px;color:#475569">'
        '准备好开始评估了吗？</div>'
        '<div style="font-size:0.95rem">'
        '填写岗位信息 · 上传简历 · 点击「开始分析」</div>'
        '</div>',
        unsafe_allow_html=True
    )
