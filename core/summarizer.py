import json
from pathlib import Path
from typing import List, Dict, Any


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "summary_prompt.txt"


def load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _lazy_call_llm():
    from services.model_router import call_llm
    return call_llm


def _candidate_snapshot(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rank": candidate.get("rank", 0),
        "name": candidate.get("name", ""),
        "score": candidate.get("score", 0),
        "recommendation": candidate.get("recommendation", ""),
        "confidence": candidate.get("confidence", 0),
        "summary": candidate.get("summary", ""),
        "strengths": candidate.get("strengths", []),
        "weaknesses": candidate.get("weaknesses", []),
        "risks": candidate.get("risks", []),
        "sub_scores": candidate.get("sub_scores", {}),
    }


def _build_context(job_title: str, jd: str, criteria: str, candidates: List[Dict[str, Any]]) -> str:
    payload = {
        "job_title": job_title,
        "jd": jd,
        "criteria": criteria,
        "candidates": [_candidate_snapshot(x) for x in candidates],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _fallback_summary(job_title: str, ranked: List[Dict[str, Any]]) -> str:
    if not ranked:
        return "暂无可用候选人数据。"

    top = ranked[0]
    avg_score = sum(x.get("score", 0) for x in ranked) / len(ranked)
    strong = [x for x in ranked if x.get("recommendation") in ("强烈推荐", "推荐")]

    lines = [
        "## 总体判断",
        f"岗位：{job_title}",
        f"候选人数：{len(ranked)}",
        f"平均分：{avg_score:.1f}",
        "",
        "## 推荐结论",
        f"优先面试：{top.get('name', '')}（{top.get('score', 0)} 分，{top.get('recommendation', '')}）",
        f"备选推荐：{', '.join(x.get('name', '') for x in strong[1:3]) if len(strong) > 1 else '暂无'}",
        "",
        "## 主要风险",
    ]

    risk_items = []
    for item in ranked[:3]:
        if item.get("risks"):
            risk_items.append(f"{item.get('name', '')}：{item['risks'][0]}")
    if risk_items:
        lines.extend(f"- {x}" for x in risk_items)
    else:
        lines.append("- 暂无显著风险")

    lines.extend(
        [
            "",
            "## 面试建议",
            "- 先验证最强候选人的项目细节与真实贡献。",
            "- 对推荐候选人重点追问业务理解、协作能力和落地能力。",
            "- 对观察候选人重点补充一致性验证。",
        ]
    )
    return "\n".join(lines)


def _fallback_comparison(job_title: str, candidates: List[Dict[str, Any]]) -> str:
    if len(candidates) < 2:
        return "至少需要两位候选人。"

    ranked = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
    best = ranked[0]
    second = ranked[1]

    lines = [
        "## 对比结论",
        f"岗位：{job_title}",
        f"优先推荐：{best.get('name', '')}",
        f"次优备选：{second.get('name', '')}",
        "",
        "## 选择理由",
        f"- {best.get('name', '')}：总分更高，且推荐等级更优。",
        f"- {second.get('name', '')}：可作为备选，但仍需补充验证。",
        "",
        "## 进一步验证点",
        "- 核实关键项目贡献是否真实。",
        "- 询问具体方法、过程与结果。",
        "- 对风险项做交叉验证。",
    ]
    return "\n".join(lines)


def summarize(job_title: str, jd: str, criteria: str, ranked: List[Dict[str, Any]]) -> str:
    if not ranked:
        return "暂无候选人数据。"

    prompt = load_prompt()
    if not prompt:
        return _fallback_summary(job_title, ranked)

    context = _build_context(job_title, jd, criteria, ranked[:8])
    user_prompt = (
        f"岗位名称：{job_title}\n\n"
        f"岗位JD：\n{jd}\n\n"
        f"评估标准：\n{criteria}\n\n"
        f"候选人数据：\n{context}\n\n"
        "请输出简洁、可执行的 Markdown，总结结构建议包含：\n"
        "1. 总体判断\n"
        "2. 推荐结论\n"
        "3. 主要风险\n"
        "4. 面试建议\n"
        "不要输出代码块，不要输出多余解释。"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        return _lazy_call_llm()(messages)
    except Exception:
        return _fallback_summary(job_title, ranked)


def compare_candidates(
    job_title: str,
    jd: str,
    criteria: str,
    candidates: List[Dict[str, Any]],
) -> str:
    if len(candidates) < 2:
        return "至少需要两位候选人。"

    prompt = load_prompt()
    if not prompt:
        return _fallback_comparison(job_title, candidates)

    context = _build_context(job_title, jd, criteria, candidates)
    user_prompt = (
        f"岗位名称：{job_title}\n\n"
        f"岗位JD：\n{jd}\n\n"
        f"评估标准：\n{criteria}\n\n"
        f"对比候选人数据：\n{context}\n\n"
        "请输出 Markdown，对比结构建议包含：\n"
        "1. 对比结论\n"
        "2. 每位候选人的优势和风险\n"
        "3. 最优推荐\n"
        "4. 下一步验证点\n"
        "不要输出代码块，不要输出多余解释。"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        return _lazy_call_llm()(messages)
    except Exception:
        return _fallback_comparison(job_title, candidates)
