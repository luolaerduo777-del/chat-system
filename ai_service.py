import os
import json
import requests

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def stream_ai(message: str, mode: str = "default", context: str = ""):
    url = "https://api.deepseek.com/chat/completions"

    system_prompts = {
        "default": "你是校园聊天室里的AI助手。回答用中文，简洁、友好、清晰。",
        "summary": "你是聊天总结助手。请根据聊天记录，总结重点内容，条理清楚，中文输出。",
        "notes": "你是学习笔记助手。请把内容整理成清晰的学习笔记，包含重点、解释和小结。",
        "teacher": "你是耐心的老师。请用通俗易懂的方式解释问题，可以举例。",
        "senior": "你是一个靠谱的学长。请用轻松、实用、接地气的方式回答。",
        "funny": "你是一个吐槽风格的AI助手。回答可以幽默一点，但不要攻击别人。"
    }

    if not API_KEY:
        yield "AI暂时不可用：未配置 DEEPSEEK_API_KEY"
        return

    system_prompt = system_prompts.get(mode, system_prompts["default"])

    user_content = message
    if context:
        user_content = f"以下是聊天室最近记录：\n{context}\n\n用户问题：{message}"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "stream": True
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            stream=True,
            timeout=120
        )
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            if line.startswith("data: "):
                line = line[6:]

            if line == "[DONE]":
                break

            try:
                chunk = json.loads(line)
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except Exception:
                continue

    except Exception as e:
        yield f"AI暂时不可用：{e}"