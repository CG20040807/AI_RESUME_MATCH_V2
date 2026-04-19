import json
import re
from typing import Any, Dict, List, Optional


SUB_SCORE_KEYS = ["技能匹配", "经验匹配", "教育背景", "综合潜力", "表达沟通"]


def _coerce_int(value, default=0):
    try:
        if value is None:
            return default
        return int(round(float(value)))
    except Exception:
        return default


def _extract_json_payload(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    content = str(text).strip()

    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.S | re.I)
    if fence:
        content = fence.group(1).strip()

    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        content = content[start : end + 1]

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}

    return {}


def _as_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, tuple):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        lines = re.split(r"[;\n；、]+", text)
        cleaned = [line.strip(" -•\t") for line in lines if line.strip(" -•\t")]
        return cleaned
    return [str(value).strip()] if str(value).strip() else []


def extract_score(text: str) -> int:
    if not text:
        return 0

    data = _extract_json_payload(text)
    if "score" in data:
        return _coerce_int(data.get("score"), 0)

    patterns = [
        r"综合评分[:：]\s*(\d+)\s*/\s*100",
        r"总分[:：]\s*(\d+)\s*/\s*100",
        r"综合评分[:：]\s*(\d+)",
        r"总分[:：]\s*(\d+)",
        r"评分[:：]\s*(\d+)",
        r"(?:score|Score)[:：]\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _coerce_int(match.group(1), 0)

    return 0


def extract_recommendation(text: str) -> str:
    if not text:
        return "无法评估"

    data = _extract_json_payload(text)
    rec = data.get("recommendation")
    if rec:
        return str(rec).strip()

    patterns = [
        r"推荐建议[:：]\s*(强烈推荐|推荐|观察|不推荐)",
        r"推荐意见[:：]\s*(强烈推荐|推荐|观察|不推荐)",
        r"推荐[:：]\s*(强烈推荐|推荐|观察|不推荐)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return "未提取"


def extract_sub_scores(text: str) -> Dict[str, Optional[int]]:
    result = {key: None for key in SUB_SCORE_KEYS}
    if not text:
        return result

    data = _extract_json_payload(text)
    raw_sub = data.get("sub_scores") or data.get("dimensions") or {}

    if isinstance(raw_sub, dict):
        alias_map = {
            "技能匹配": ["技能匹配", "skills", "skill", "skill_match"],
            "经验匹配": ["经验匹配", "experience", "exp", "experience_match"],
            "教育背景": ["教育背景", "education", "edu"],
            "综合潜力": ["综合潜力", "potential", "growth", "potential_score"],
            "表达沟通": ["表达沟通", "communication", "communicate"],
        }
        for key, aliases in alias_map.items():
            for alias in aliases:
                if alias in raw_sub and raw_sub[alias] is not None:
                    result[key] = _coerce_int(raw_sub[alias], None)
                    break

        if any(v is not None for v in result.values()):
            return result

    for key in SUB_SCORE_KEYS:
        pattern = rf"{re.escape(key)}[:：]\s*(\d+)"
        match = re.search(pattern, text)
        if match:
            result[key] = _coerce_int(match.group(1), None)

    return result


def parse_analysis_result(text: str) -> Dict[str, Any]:
    raw_json = _extract_json_payload(text)

    score = extract_score(text)
    recommendation = extract_recommendation(text)
    summary = str(raw_json.get("summary") or raw_json.get("conclusion") or "").strip()

    strengths = _as_list(raw_json.get("strengths") or raw_json.get("优势"))
    weaknesses = _as_list(raw_json.get("weaknesses") or raw_json.get("不足"))
    risks = _as_list(raw_json.get("risks") or raw_json.get("风险"))
    questions = _as_list(
        raw_json.get("interview_questions")
        or raw_json.get("questions")
        or raw_json.get("面试问题")
    )

    match_reason = str(
        raw_json.get("match_reason")
        or raw_json.get("analysis")
        or raw_json.get("reason")
        or ""
    ).strip()

    confidence = _coerce_int(raw_json.get("confidence"), 0)
    sub_scores = extract_sub_scores(text)

    if not summary:
        summary = match_reason or "暂无摘要"

    return {
        "score": score,
        "recommendation": recommendation,
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risks": risks,
        "questions": questions,
        "match_reason": match_reason,
        "confidence": confidence,
        "sub_scores": sub_scores,
        "raw_json": raw_json,
        "raw_text": text or "",
    }
