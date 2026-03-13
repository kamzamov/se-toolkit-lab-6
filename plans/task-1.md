# Task 1 Plan: Call an LLM from Code

## LLM Provider
- Provider: Qwen Code API (self-hosted on VM)
- Model: qwen3-coder-plus
- Endpoint: http://10.93.25.19:42005/v1

## Agent Architecture
1. Parse CLI argument (question)
2. Load env vars from .env.agent.secret (python-dotenv)
3. Build OpenAI-compatible request to /v1/chat/completions
4. Parse response, extract content
5. Output JSON: {"answer": "...", "tool_calls": []}

## Error Handling
- Network errors → stderr + exit 1
- Invalid JSON response → stderr + exit 1
- Timeout >60s → handled by requests library

## Testing
- One regression test: run agent.py, parse stdout, validate fields
