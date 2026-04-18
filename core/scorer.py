import re


def extract_score(text: str) -> float:
    """
    从分析文本中提取总分。
    依次匹配：「总分：xx/100」→「总分：xx」→「评分：xx」→ 默认50
    """
    if not text:
        return 0.0

    m = re.search(r"总分[:：]\s*(\d+)\s*/\s*100", text)
    if m:
        return float(m.group(1))

    m = re.search(r"总分[:：]\s*(\d+)", text)
    if m:
        return float(m.group(1))

    m = re.search(r"(?:评分|score)[:：]\s*(\d+)", text, re.I)
    if m:
        return float(m.group(1))

    return 50.0
