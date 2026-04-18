import re


def clean_text(text: str) -> str:
    """清理简历文本中的特殊字符和多余空白。"""
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
