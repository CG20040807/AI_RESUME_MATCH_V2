import io
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _font(run, bold=False, size=11, color=None):
    run.font.name = "微软雅黑"
    run.font.size = Pt(size)
    run.bold      = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def _section(doc, title, body, level=1):
    doc.add_heading(title, level=level)
    doc.add_paragraph(body if body and body.strip() else "暂无内容")


def export_to_docx(job_title, jd, criteria, results, summary):
    """生成完整评估报告，返回 BytesIO。"""
    doc = Document()

    # 封面
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = tp.add_run("AI 智能人才评估报告")
    _font(tr, bold=True, size=22)

    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sp.add_run("岗位：" + job_title)
    _font(sr, size=13, color=(80, 80, 80))

    doc.add_paragraph("")

    # 岗位信息
    _section(doc, "一、岗位信息", "")
    _section(doc, "岗位名称", job_title, level=2)
    _section(doc, "岗位JD", jd, level=2)
    _section(doc, "评估标准", criteria, level=2)

    # 综合总结
    doc.add_page_break()
    _section(doc, "二、综合总结", summary)

    # 排名列表
    doc.add_page_break()
    doc.add_heading("三、候选人排名", level=1)
    for idx, r in enumerate(results, 1):
        p   = doc.add_paragraph()
        run = p.add_run(
            "第" + str(idx) + "名  " + r["name"] +
            "  —  " + str(r["score"]) + "分" +
            "  —  " + r.get("recommendation", "未提取")
        )
        _font(run, bold=(idx == 1), size=11)

    # 逐人详情
    for idx, r in enumerate(results, 1):
        doc.add_page_break()
        doc.add_heading("四-" + str(idx) + ". " + r["name"], level=1)

        ip  = doc.add_paragraph()
        ir  = ip.add_run(
            "综合得分：" + str(r.get("score", 0)) + " 分    " +
            "推荐意见：" + r.get("recommendation", "未提取")
        )
        _font(ir, bold=True)

        sub = r.get("sub_scores", {})
        if sub and any(v is not None for v in sub.values()):
            doc.add_heading("评分详情", level=2)
            for k, v in sub.items():
                if v is not None:
                    doc.add_paragraph(k + "：" + str(v) + "/100",
                                      style="List Bullet")

        doc.add_heading("详细分析", level=2)
        doc.add_paragraph(r.get("analysis", "暂无"))

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


def export_single_to_docx(job_title, jd, criteria, candidate):
    """生成单个候选人报告，返回 BytesIO。"""
    doc = Document()

    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = tp.add_run(candidate["name"] + " — 候选人评估报告")
    _font(tr, bold=True, size=20)

    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sp.add_run("应聘岗位：" + job_title)
    _font(sr, size=12, color=(80, 80, 80))

    doc.add_paragraph("")

    doc.add_heading("一、评估摘要", level=1)
    p   = doc.add_paragraph()
    run = p.add_run(
        "综合得分：" + str(candidate.get("score", 0)) + " / 100\n" +
        "推荐意见：" + candidate.get("recommendation", "未提取")
    )
    _font(run, bold=True, size=12)

    sub = candidate.get("sub_scores", {})
    if sub and any(v is not None for v in sub.values()):
        doc.add_heading("二、各维度评分", level=1)
        for k, v in sub.items():
            if v is not None:
                doc.add_paragraph(k + "：" + str(v) + " / 100",
                                  style="List Bullet")

    doc.add_heading("三、详细分析", level=1)
    doc.add_paragraph(candidate.get("analysis", "暂无"))

    doc.add_page_break()
    _section(doc, "四、岗位信息（参考）", "")
    _section(doc, "岗位JD", jd, level=2)
    _section(doc, "评估标准", criteria, level=2)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
