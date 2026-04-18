from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "candidate_prompt.txt"

def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def analyze(job_title, jd, criteria, resume_text):
    prompt_template = load_prompt()

    return f"""
【模拟分析结果】
岗位：{job_title}
评分：75
推荐建议：推荐

（说明：这是mock数据，说明你的系统路径没问题）
"""
