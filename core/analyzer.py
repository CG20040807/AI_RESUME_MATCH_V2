from pathlib import Path
from services.model_router import call_llm

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "summary_prompt.txt"


def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def summarize(job_title, jd, criteria, results):
    prompt_template = load_prompt()

    lines = [
        r["name"] + "：" + str(r["score"]) + "分，" + r.get("recommendation", "未提取")
        for r in results
    ]

    user_prompt = (
        "岗位名称：\n" + job_title + "\n\n"
        "岗位JD：\n" + jd + "\n\n"
        "岗位评估标准：\n" + criteria + "\n\n"
        "候选人列表（已按分数排序）：\n" + "\n".join(lines) + "\n\n"
        "请基于这些候选人结果，输出总结报告。"
    )

    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user",   "content": user_prompt}
    ]
    return call_llm(messages)
