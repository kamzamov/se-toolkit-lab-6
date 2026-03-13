#!/usr/bin/env python3
import json
import os
import re
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

# Project root for security checks
PROJECT_ROOT = Path(__file__).parent.resolve()

# Maximum tool calls per question
MAX_TOOL_CALLS = 10

# System prompt for the documentation agent
SYSTEM_PROMPT = """You are a documentation assistant. You have access to a project wiki with documentation files.

Your task is to answer user questions by reading the wiki files.

Available tools:
- list_files: List files and directories at a given path
- read_file: Read the contents of a file

Process:
1. Use list_files to explore the wiki directory structure
2. Use read_file to read relevant files
3. Find the answer and identify the source (file path and section if applicable)
4. Provide a clear answer with the source reference

IMPORTANT: You must respond with ONLY valid JSON. No other text.

To call a tool, respond with EXACTLY this JSON format:
{"tool_call": {"name": "tool_name", "arguments": {"path": "path/to/file"}}}

To give a final answer, respond with EXACTLY this JSON format:
{"final_answer": {"answer": "your answer here", "source": "wiki/file.md#section-anchor"}}

For the source field, use the file path where you found the answer. If there's a relevant section, include it with #anchor format (lowercase, hyphens instead of spaces).
Example: wiki/git-workflow.md#resolving-merge-conflicts
"""


def is_safe_path(path: str) -> bool:
    """Check if path is safe (no directory traversal)."""
    if ".." in path or path.startswith("/"):
        return False
    return True


def read_file(path: str) -> str:
    """Read a file from the project repository."""
    if not is_safe_path(path):
        return "Error: Access denied - invalid path"
    
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        return f"Error: File not found - {path}"
    if not full_path.is_file():
        return f"Error: Not a file - {path}"
    
    try:
        return full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: Could not read file - {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path."""
    if not is_safe_path(path):
        return "Error: Access denied - invalid path"
    
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        return f"Error: Directory not found - {path}"
    if not full_path.is_dir():
        return f"Error: Not a directory - {path}"
    
    try:
        entries = sorted([e.name for e in full_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error: Could not list directory - {e}"


TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files
}


def call_llm(messages: list) -> str:
    """Send messages to LLM and return response content."""
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool and return result."""
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool - {tool_name}"
    
    func = TOOL_FUNCTIONS[tool_name]
    try:
        if "path" in args:
            return func(args["path"])
        return func(**args)
    except Exception as e:
        return f"Error: Tool execution failed - {e}"


def extract_json_from_response(content: str) -> dict | None:
    """Extract JSON object from LLM response."""
    content = content.strip()
    
    # Try to find JSON object in the content
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try parsing the whole content as JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def run_agent(question: str) -> dict:
    """Run the agentic loop and return result."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    source = ""
    answer = ""
    
    for iteration in range(MAX_TOOL_CALLS):
        try:
            response_content = call_llm(messages)
        except Exception as e:
            print(f"LLM API error: {e}", file=sys.stderr)
            return {
                "answer": f"Error: LLM API failed - {e}",
                "source": "",
                "tool_calls": tool_calls_log
            }
        
        parsed = extract_json_from_response(response_content)
        
        if parsed is None:
            # Could not parse JSON, treat as final answer
            answer = response_content
            if tool_calls_log:
                for tc in reversed(tool_calls_log):
                    if tc["tool"] == "read_file":
                        source = tc["args"].get("path", "")
                        break
            break
        
        # Check for tool call
        if "tool_call" in parsed:
            tool_call = parsed["tool_call"]
            tool_name = tool_call.get("name", "")
            args = tool_call.get("arguments", {})
            
            result = execute_tool(tool_name, args)
            
            tool_calls_log.append({
                "tool": tool_name,
                "args": args,
                "result": result
            })
            
            # Add to messages for context
            messages.append({"role": "assistant", "content": response_content})
            messages.append({"role": "user", "content": f"Tool result: {result}"})
            
        elif "final_answer" in parsed:
            final = parsed["final_answer"]
            answer = final.get("answer", "")
            source = final.get("source", "")
            
            # If source is empty but we have tool calls, use the last read_file path
            if not source and tool_calls_log:
                for tc in reversed(tool_calls_log):
                    if tc["tool"] == "read_file":
                        source = tc["args"].get("path", "")
                        break
            
            break
        else:
            # Unknown format, treat as final answer
            answer = response_content
            if tool_calls_log:
                for tc in reversed(tool_calls_log):
                    if tc["tool"] == "read_file":
                        source = tc["args"].get("path", "")
                        break
            break
    
    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_log
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    try:
        result = run_agent(question)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
