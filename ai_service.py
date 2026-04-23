import os
import requests

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def ask_ai(message: str) -> str:
    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是校园聊天室里的AI助手。回答用中文，简洁、友好、清晰。"
            },
            {
                "role": "user",
                "content": message
            }
        ],
        "stream": False
    }

    try:
        if not API_KEY:
            return "AI暂时不可用：未配置 DEEPSEEK_API_KEY"

        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"AI暂时不可用：{e}"