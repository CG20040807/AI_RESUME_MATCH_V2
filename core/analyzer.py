from pathlib import Path
from services.model_router import call_llm

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "candidate_prompt.txt"


def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def analyze(job_title, jd, criteria, resume_text):
    prompt_template = load_prompt()

    user_prompt = (
        "岗位名称：\n" + job_title + "\n\n"
        "岗位JD：\n" + jd + "\n\n"
        "岗位评估标准：\n" + criteria + "\n\n"
        "候选人简历：\n" + resume_text + "\n\n"
        "请严格按照模板输出。"
    )

    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user",   "content": user_prompt}
    ]

    return call_llm(messages)
