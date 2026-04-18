import time
from services.qwen_client import call_qwen
from services.deepseek_client import call_deepseek

MODEL_PRIORITY = ["qwen", "deepseek"]


def safe_call(func, messages, retries=2, sleep_sec=0.5):
    last_err = None
    for attempt in range(retries):
        try:
            return func(messages)
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(sleep_sec)
    raise last_err


def call_llm(messages):
    errors = []
    for model in MODEL_PRIORITY:
        try:
            if model == "qwen":
                return safe_call(call_qwen, messages)
            if model == "deepseek":
                return safe_call(call_deepseek, messages)
        except Exception as e:
            errors.append(model + ": " + str(e))
            continue

    return "⚠️ AI 服务暂时不可用，请检查 API Key。错误：" + " | ".join(errors)
