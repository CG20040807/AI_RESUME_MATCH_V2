import os
from openai import OpenAI


def call_deepseek(messages):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，请检查 .env 文件")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.2,
        timeout=90
    )
    return resp.choices[0].message.content.strip()
