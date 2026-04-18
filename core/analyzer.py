from pathlib import Path
from services.model_router import call_llm

# ========= 路径配置 =========
BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "candidate_prompt.txt"


# ========= Prompt加载 =========
def load_prompt():
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"❌ Prompt加载失败: {str(e)}"


# ========= 主分析函数 =========
def analyze(job_title, jd, criteria, resume_text):
    """
    输入：
        job_title: 岗位名称
        jd: 岗位JD
        criteria: 评估标准
        resume_text: 简历文本

    输出：
        str: LLM分析结果
    """

    # 1️⃣ 基础校验（防炸）
    if not job_title or not jd or not criteria or not resume_text:
        return "⚠️ 输入信息不完整，无法进行分析"

    # 2️⃣ 加载Prompt模板
    prompt_template = load_prompt()

    # 如果Prompt加载失败，直接返回
    if prompt_template.startswith("❌"):
        return prompt_template

    # 3️⃣ 构造用户Prompt
    user_prompt = (
        f"岗位名称：\n{job_title}\n\n"
        f"岗位JD：\n{jd}\n\n"
        f"岗位评估标准：\n{criteria}\n\n"
        f"候选人简历：\n{resume_text}\n\n"
        f"请严格按照模板输出。"
    )

    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": user_prompt}
    ]

    # 4️⃣ 调用模型（带兜底）
    try:
        result = call_llm(messages)

        # 防止返回None或空
        if not result or len(result.strip()) == 0:
            return "⚠️ AI返回为空，请检查模型服务"

        return result

    except Exception as e:
        return f"❌ AI分析异常: {str(e)}"
