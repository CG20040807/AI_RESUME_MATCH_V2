import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from core.analyzer import analyze
from core.ranker import rank_candidates
from core.scorer import parse_analysis_result
from core.summarizer import compare_candidates, summarize
from utils.docx_exporter import export_single_to_docx, export_to_docx
from utils.file_parser import parse_docx
from utils.text_cleaner import clean_text

st.set_page_config(
    page_title="AI 简历评估系统",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.stApp {
    background: #f6f7fb;
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}
.card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
}
.best-box {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 18px 20px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
}
.section-title {
    font-size: 1rem;
    font-weight: 700;
    margin: 0 0 12px 0;
    color: #111827;
}
.muted {
    color: #6b7280;
    font-size: 0.92rem;
}
.small {
    color: #6b7280;
    font-size: 0.86rem;
}
.subtle {
    color: #374151;
}
hr {
    border-color: #e5e7eb;
}
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
}
[data-testid="stSidebar"] * {
    color: #111827;
}
</style>
""",
    unsafe_allow_html=True,
)

DEFAULTS = {
    "results": [],
    "summary": "",
    "word_bytes": None,
    "job_title_cache": "",
    "jd_cache": "",
    "criteria_cache": "",
    "logs": [],
    "expanded_all": False,
    "comparison_md": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def join_lines(items):
    if not items:
        return "暂无"
    return "\n".join(f"- {x}" for x in items)


def flatten_results_for_table(results):
    rows = []
    for item in results:
        rows.append(
            {
                "排名": item.get("rank", 0),
                "姓名": item.get("name", ""),
                "总分": item.get("score", 0),
                "推荐意见": item.get("recommendation", ""),
                "置信度": item.get("confidence", 0),
                "摘要": item.get("summary", ""),
                "优势": "；".join(item.get("strengths", [])),
                "不足": "；".join(item.get("weaknesses", [])),
                "风险": "；".join(item.get("risks", [])),
            }
        )
    return pd.DataFrame(rows)


def results_to_json_bytes(results):
    payload = []
    for item in results:
        payload.append(
            {
                "rank": item.get("rank", 0),
                "name": item.get("name", ""),
                "score": item.get("score", 0),
                "recommendation": item.get("recommendation", ""),
                "confidence": item.get("confidence", 0),
                "summary": item.get("summary", ""),
                "match_reason": item.get("match_reason", ""),
                "strengths": item.get("strengths", []),
                "weaknesses": item.get("weaknesses", []),
                "risks": item.get("risks", []),
                "questions": item.get("questions", []),
                "sub_scores": item.get("sub_scores", {}),
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def results_to_csv_bytes(results):
    df = flatten_results_for_table(results)
    return df.to_csv(index=False).encode("utf-8-sig")


with st.sidebar:
    st.title("简历评估系统")
    st.caption("结构化解析、评分、排序、总结、导出")
    st.divider()

    st.subheader("筛选与排序")
    score_threshold = st.slider("最低分数门槛", 0, 100, 60, 5)
    all_recs = ["强烈推荐", "推荐", "观察", "不推荐", "未提取", "无法评估"]
    rec_filter = st.multiselect("推荐等级", all_recs, default=all_recs)
    sort_by = st.radio("排序方式", ["综合评分（高到低）", "综合评分（低到高）", "文件名"], index=0)

    st.divider()
    st.subheader("说明")
    st.write("1. 填写岗位信息")
    st.write("2. 粘贴岗位 JD 和评估标准")
    st.write("3. 上传 docx 简历")
    st.write("4. 点击开始分析")
    st.write("5. 查看总结、对比和导出")

    if st.session_state.results:
        st.divider()
        st.subheader("当前数据")
        rs = st.session_state.results
        st.metric("候选人数", len(rs))
        st.metric("平均分", f"{sum(x['score'] for x in rs) / len(rs):.1f}")
        st.metric("推荐人数", sum(1 for x in rs if x.get("recommendation") in ("强烈推荐", "推荐")))


st.title("AI 简历评估系统")
st.caption("把简历筛选从“看文本”升级成“看结构、看结论、看决策”。")

st.markdown('<div class="card"><div class="section-title">岗位信息与简历上传</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1.2, 1.2, 1.0])

with col1:
    job_title = st.text_input(
        "岗位名称",
        value=st.session_state.job_title_cache,
        placeholder="例如：产品经理实习生",
    )
    jd = st.text_area(
        "岗位 JD",
        value=st.session_state.jd_cache,
        height=190,
        placeholder="粘贴岗位描述，越完整越好。",
    )

with col2:
    criteria = st.text_area(
        "评估标准",
        value=st.session_state.criteria_cache,
        height=130,
        placeholder="例如：产品实习经历、逻辑表达、数据分析能力等。",
    )
    extra_notes = st.text_area(
        "补充备注",
        height=100,
        placeholder="例如：只看本季度可到岗者、偏好有校招经验者等。",
    )

with col3:
    uploaded_files = st.file_uploader(
        "上传简历",
        type=["docx"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        st.success(f"已上传 {len(uploaded_files)} 份简历")
        for f in uploaded_files:
            st.write(f.name)
    else:
        st.info("支持批量上传 .docx 文件。")

st.markdown("</div>", unsafe_allow_html=True)

btn1, btn2, btn3, btn4 = st.columns([2, 1, 1, 1])
with btn1:
    start_btn = st.button("开始分析", use_container_width=True, type="primary")
with btn2:
    clear_btn = st.button("清空输入", use_container_width=True)
with btn3:
    demo_btn = st.button("填入示例", use_container_width=True)
with btn4:
    help_btn = st.button("使用说明", use_container_width=True)

if clear_btn:
    st.session_state.job_title_cache = ""
    st.session_state.jd_cache = ""
    st.session_state.criteria_cache = ""
    st.session_state.expanded_all = False
    st.rerun()

if demo_btn:
    st.session_state.job_title_cache = "AI产品经理实习生"
    st.session_state.jd_cache = (
        "负责AI产品从0到1的设计与迭代，包括需求分析、PRD撰写、"
        "与技术团队协作推进落地，跟进产品数据并持续优化用户体验。"
    )
    st.session_state.criteria_cache = (
        "优先有产品实习经验；熟悉AI工具使用；具备数据分析能力；"
        "逻辑表达清晰；计算机或数据相关专业加分。"
    )
    st.rerun()

if help_btn:
    st.info(
        "先填岗位名称、JD 和评估标准，再上传简历。分析完成后可以查看总览、逐人详情、候选人对比和导出报告。"
    )

if start_btn:
    errors = []
    if not job_title.strip():
        errors.append("请填写岗位名称")
    if not jd.strip():
        errors.append("请填写岗位 JD")
    if not criteria.strip():
        errors.append("请填写评估标准")
    if not uploaded_files:
        errors.append("请上传至少一份简历")

    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    st.session_state.job_title_cache = job_title.strip()
    st.session_state.jd_cache = jd.strip()
    st.session_state.criteria_cache = criteria.strip()

    full_criteria = criteria.strip()
    if extra_notes.strip():
        full_criteria = full_criteria + "\n\n补充备注：\n" + extra_notes.strip()

    results = []
    logs = []
    progress = st.progress(0)
    status_box = st.empty()

    for idx, file in enumerate(uploaded_files, start=1):
        candidate_name = Path(file.name).stem
        status_box.markdown(f"正在分析 {idx}/{len(uploaded_files)}：{candidate_name}")

        raw_text = parse_docx(file)
        if not raw_text or str(raw_text).startswith("【"):
            result = {
                "name": candidate_name,
                "score": 0,
                "recommendation": "无法评估",
                "confidence": 0,
                "summary": "简历解析失败",
                "match_reason": "",
                "strengths": [],
                "weaknesses": [],
                "risks": [],
                "questions": [],
                "sub_scores": {},
                "raw_analysis": str(raw_text),
                "raw_json": {},
            }
            logs.append(f"{candidate_name}：解析失败")
        else:
            resume_text = clean_text(raw_text)
            analysis_text = analyze(job_title, jd, full_criteria, resume_text)
            parsed = parse_analysis_result(analysis_text)

            result = {
                "name": candidate_name,
                "score": parsed["score"],
                "recommendation": parsed["recommendation"],
                "confidence": parsed["confidence"],
                "summary": parsed["summary"],
                "match_reason": parsed["match_reason"],
                "strengths": parsed["strengths"],
                "weaknesses": parsed["weaknesses"],
                "risks": parsed["risks"],
                "questions": parsed["questions"],
                "sub_scores": parsed["sub_scores"],
                "raw_analysis": analysis_text,
                "raw_json": parsed["raw_json"],
            }
            logs.append(f"{candidate_name}：{result['score']} 分，{result['recommendation']}")

        results.append(result)
        progress.progress(idx / len(uploaded_files))

    ranked = rank_candidates(results)
    summary_md = summarize(job_title, jd, full_criteria, ranked)

    try:
        word_bytes = export_to_docx(job_title, jd, full_criteria, ranked, summary_md)
    except Exception as exc:
        word_bytes = None
        st.warning(f"Word 导出失败：{exc}")

    st.session_state.results = ranked
    st.session_state.summary = summary_md
    st.session_state.word_bytes = word_bytes
    st.session_state.logs = logs
    st.session_state.comparison_md = ""

    st.success(f"分析完成，共处理 {len(uploaded_files)} 份简历。")
    st.rerun()

if st.session_state.results:
    ranked = st.session_state.results

    if sort_by == "综合评分（高到低）":
        display_results = sorted(ranked, key=lambda x: x["score"], reverse=True)
    elif sort_by == "综合评分（低到高）":
        display_results = sorted(ranked, key=lambda x: x["score"])
    else:
        display_results = sorted(ranked, key=lambda x: x["name"])

    display_results = [
        item for item in display_results if item.get("recommendation", "未提取") in rec_filter
    ]

    st.divider()
    st.subheader("结果总览")

    total_n = len(ranked)
    avg_score = sum(x["score"] for x in ranked) / total_n if total_n else 0
    best = ranked[0] if ranked else {}
    best_count = sum(1 for x in ranked if x.get("recommendation") in ("强烈推荐", "推荐"))
    pass_count = sum(1 for x in ranked if x["score"] >= score_threshold)

    metric_cols = st.columns(4)
    metric_cols[0].metric("候选人数", total_n)
    metric_cols[1].metric("平均分", f"{avg_score:.1f}")
    metric_cols[2].metric("达标人数", pass_count)
    metric_cols[3].metric("推荐人数", best_count)

    if best:
        st.markdown('<div class="best-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">推荐面试对象</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("姓名", best["name"])
            st.metric("总分", best["score"])
            st.metric("推荐意见", best.get("recommendation", "未提取"))
        with c2:
            st.write(best.get("summary", ""))
            if best.get("match_reason"):
                st.markdown("**匹配原因**")
                st.write(best["match_reason"])
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 排名表")
    overview_df = flatten_results_for_table(ranked)
    st.dataframe(overview_df, use_container_width=True, hide_index=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["总览详情", "逐人详情", "候选人对比", "综合总结", "导出"]
    )

    with tab1:
        st.write("根据当前排序和筛选条件展示结果。")
        for item in display_results:
            with st.expander(
                f"第 {item.get('rank', 0)} 名  |  {item['name']}  |  {item['score']} 分  |  {item.get('recommendation', '未提取')}"
            ):
                left, right = st.columns([1, 2])
                with left:
                    st.metric("总分", item["score"])
                    st.metric("推荐意见", item.get("recommendation", "未提取"))
                    st.metric("置信度", item.get("confidence", 0))
                    if item.get("sub_scores"):
                        st.markdown("**分项评分**")
                        for k, v in item["sub_scores"].items():
                            st.write(f"{k}：{v if v is not None else '未提取'}")
                with right:
                    st.markdown("**摘要**")
                    st.write(item.get("summary", ""))
                    st.markdown("**优势**")
                    st.write(join_lines(item.get("strengths", [])))
                    st.markdown("**不足**")
                    st.write(join_lines(item.get("weaknesses", [])))
                    st.markdown("**风险**")
                    st.write(join_lines(item.get("risks", [])))
                    st.markdown("**面试问题**")
                    st.write(join_lines(item.get("questions", [])))

    with tab2:
        st.write("每位候选人的完整结构化结果。")
        for i, item in enumerate(display_results):
            exp = st.session_state.expanded_all or i == 0
            with st.expander(
                f"{item['name']}  |  {item['score']} 分  |  {item.get('recommendation', '未提取')}",
                expanded=exp,
            ):
                left, right = st.columns([1, 2])
                with left:
                    st.metric("总分", item["score"])
                    st.metric("推荐意见", item.get("recommendation", "未提取"))
                    st.metric("置信度", item.get("confidence", 0))
                    if item.get("sub_scores"):
                        st.markdown("**分项评分**")
                        for k, v in item["sub_scores"].items():
                            st.write(f"{k}：{v if v is not None else '未提取'}")
                with right:
                    st.markdown("**匹配原因**")
                    st.write(item.get("match_reason", ""))
                    st.markdown("**摘要**")
                    st.write(item.get("summary", ""))
                    st.markdown("**优势**")
                    st.write(join_lines(item.get("strengths", [])))
                    st.markdown("**不足**")
                    st.write(join_lines(item.get("weaknesses", [])))
                    st.markdown("**风险**")
                    st.write(join_lines(item.get("risks", [])))
                    st.markdown("**面试问题**")
                    st.write(join_lines(item.get("questions", [])))

                single_bytes = export_single_to_docx(
                    st.session_state.job_title_cache,
                    st.session_state.jd_cache,
                    st.session_state.criteria_cache,
                    item,
                )
                st.download_button(
                    f"下载 {item['name']} 的单人报告",
                    data=single_bytes,
                    file_name=f"{item['name']}_评估报告.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"single_{i}",
                )

    with tab3:
        st.write("选择 2 到 5 位候选人进行对比。")
        all_names = [x["name"] for x in display_results]
        default_sel = all_names[: min(4, len(all_names))]
        selected_names = st.multiselect("选择候选人", all_names, default=default_sel)

        selected = [x for x in display_results if x["name"] in selected_names][:5]
        if len(selected) >= 2:
            compare_df = pd.DataFrame(
                [
                    {
                        "姓名": x["name"],
                        "总分": x["score"],
                        "推荐意见": x.get("recommendation", "未提取"),
                        "置信度": x.get("confidence", 0),
                        "摘要": x.get("summary", ""),
                        "风险": "；".join(x.get("risks", [])),
                    }
                    for x in selected
                ]
            )
            st.dataframe(compare_df, use_container_width=True, hide_index=True)

            if st.button("生成对比结论"):
                with st.spinner("正在生成对比结论..."):
                    st.session_state.comparison_md = compare_candidates(
                        st.session_state.job_title_cache,
                        st.session_state.jd_cache,
                        st.session_state.criteria_cache,
                        selected,
                    )

            if st.session_state.comparison_md:
                st.markdown(st.session_state.comparison_md)
        else:
            st.info("请至少选择 2 位候选人。")

    with tab4:
        st.markdown(st.session_state.summary or "暂无总结。")
        if st.session_state.summary:
            summary_bytes = st.session_state.summary.encode("utf-8")
            st.download_button(
                "下载总结文本",
                data=summary_bytes,
                file_name="summary.md",
                mime="text/markdown",
                use_container_width=True,
            )

    with tab5:
        st.markdown("### 导出")
        c1, c2, c3 = st.columns(3)

        with c1:
            if st.session_state.word_bytes:
                ts = datetime.now().strftime("%Y%m%d_%H%M")
                st.download_button(
                    "下载完整 Word 报告",
                    data=st.session_state.word_bytes,
                    file_name=f"{st.session_state.job_title_cache}_完整报告_{ts}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            else:
                st.button("Word 报告生成中", disabled=True, use_container_width=True)

        with c2:
            st.download_button(
                "下载 JSON",
                data=results_to_json_bytes(ranked),
                file_name=f"{st.session_state.job_title_cache}_评分数据.json",
                mime="application/json",
                use_container_width=True,
            )

        with c3:
            st.download_button(
                "下载 CSV",
                data=results_to_csv_bytes(ranked),
                file_name=f"{st.session_state.job_title_cache}_排名表.csv",
                mime="text/csv",
                use_container_width=True,
            )

    if st.session_state.logs:
        with st.expander("运行日志"):
            for line in st.session_state.logs:
                st.write(line)
else:
    st.markdown(
        """
<div class="card">
    <div class="section-title">准备开始</div>
    <div class="muted">填写岗位信息、上传简历后点击开始分析。</div>
</div>
""",
        unsafe_allow_html=True,
    )
