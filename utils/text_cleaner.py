import re


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)
    text = text.replace("\u00a0", " ")
    text = text.replace("\t", " ")
    text = re.sub(r"[ \u3000]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\r\n", "\n", text)
    text = text.strip()
    return text
