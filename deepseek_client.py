import os
from openai import OpenAI


def call_qwen(messages):
    api_key  = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL",
                         "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model    = os.getenv("QWEN_MODEL", "qwen-plus")

    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，请检查 .env 文件")

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp   = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        timeout=90
    )
    return resp.choices[0].message.content.strip()
