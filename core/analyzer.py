from pathlib import Path
from services.model_router import call_llm

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "candidate_prompt.txt"


def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def analyze(job_title, jd, criteria, resume_text):
    prompt_template = load_prompt()

    user_prompt = f"""
岗位名称：
{job_title}

岗位JD：
{jd}

岗位评估标准：
{criteria}

候选人简历：
{resume_text}

请严格按照模板输出。
"""

    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user",   "content": user_prompt}
    ]
    return call_llm(messages)
