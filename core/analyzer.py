import json
from pathlib import Path


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "candidate_prompt.txt"


def load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception as exc:
        return ""


def _fallback_payload(message: str) -> str:
    return json.dumps(
        {
            "score": 0,
            "recommendation": "无法评估",
            "summary": "分析服务不可用",
            "strengths": [],
            "weaknesses": [],
            "risks": [message],
            "interview_questions": [],
            "match_reason": message,
            "sub_scores": {
                "技能匹配": 0,
                "经验匹配": 0,
                "教育背景": 0,
                "综合潜力": 0,
                "表达沟通": 0,
            },
            "confidence": 0,
        },
        ensure_ascii=False,
        indent=2,
    )


def analyze(job_title, jd, criteria, resume_text):
    job_title = (job_title or "").strip()
    jd = (jd or "").strip()
    criteria = (criteria or "").strip()
    resume_text = (resume_text or "").strip()

    if not job_title or not jd or not criteria or not resume_text:
        return _fallback_payload("输入信息不完整")

    try:
        from services.model_router import call_llm
    except Exception as exc:
        return _fallback_payload(f"模型路由加载失败：{exc}")

    prompt_template = load_prompt()
    if not prompt_template:
        return _fallback_payload("Prompt 加载失败")

    user_prompt = (
        f"岗位名称：\n{job_title}\n\n"
        f"岗位JD：\n{jd}\n\n"
        f"岗位评估标准：\n{criteria}\n\n"
        f"候选人简历：\n{resume_text}\n\n"
        "请严格只输出 JSON，不要输出代码块、解释、前后缀文字。"
    )

    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result = call_llm(messages)
        if not result or not str(result).strip():
            return _fallback_payload("模型返回为空")
        return str(result).strip()
    except Exception as exc:
        return _fallback_payload(f"AI 分析异常：{exc}")
