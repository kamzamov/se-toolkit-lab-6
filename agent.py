#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Загружаем переменные окружения из .env.agent.secret
env_path = Path(__file__).parent / ".env.agent.secret"
load_dotenv(env_path)

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")


def call_llm(question: str) -> dict:
    """Отправляет вопрос в LLM и возвращает ответ."""
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    
    data = response.json()
    answer = data["choices"][0]["message"]["content"]
    return {"answer": answer, "tool_calls": []}


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    try:
        result = call_llm(question)
        # Только валидный JSON в stdout
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
