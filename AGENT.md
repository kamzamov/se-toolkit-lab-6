# Agent Architecture

## Overview

This agent is a CLI tool that answers questions by reading project documentation, examining source code, and querying a backend API. It uses an agentic loop to discover information from multiple sources, then synthesizes answers with source references.

## LLM Provider

- **Provider**: Qwen Code API (self-hosted on VM)
- **Model**: `qwen3-coder-plus`
- **Endpoint**: OpenAI-compatible chat completions API

## Tools

The agent has three tools for navigating the project and querying data:

### `read_file`

Reads a file from the project repository.

- **Parameters**: `path` (string) - relative path from project root
- **Returns**: File contents as string, or error message
- **Security**: Blocks paths with `../` to prevent directory traversal
- **Use cases**: Wiki documentation, source code inspection

### `list_files`

Lists files and directories at a given path.

- **Parameters**: `path` (string) - relative directory path from project root
- **Returns**: Newline-separated listing of entries, or error message
- **Security**: Blocks paths with `../` to prevent directory traversal
- **Use cases**: Exploring wiki structure, finding source files

### `query_api`

Queries the backend LMS API for real-time data.

- **Parameters**: 
  - `method` (string) - HTTP method (GET, POST, PUT, DELETE)
  - `path` (string) - API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
  - `body` (string, optional) - JSON request body for POST/PUT
- **Returns**: JSON string with `status_code` and `body`
- **Authentication**: Uses `LMS_API_KEY` from environment variables, sent as `X-API-Key` header
- **Use cases**: Item counts, analytics data, scores, system status

## Environment Variables

The agent reads all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for backend API | Optional, defaults to `http://localhost:42002` |

> **Important:** The autochecker injects different values for these variables during evaluation. Hardcoding any of these values will cause the agent to fail.

## Agentic Loop

```
Question → LLM (with system prompt) → tool call? → execute → back to LLM
                                    │
                                    no
                                    │
                                    ▼
                               JSON output
```

1. **Send question**: User question + system prompt sent to LLM
2. **Parse response**: Extract JSON to check for tool calls or final answer
3. **Execute tools**: If tool call present, execute and append result to messages
4. **Repeat**: Send updated messages back to LLM
5. **Final answer**: When LLM returns final_answer, extract answer and source
6. **Safety limit**: Maximum 10 tool calls per question

## Output Format

```json
{
  "answer": "The answer text from the LLM",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": {...}}"
    }
  ]
}
```

- `answer` (string): The LLM's final answer
- `source` (string): File path where the answer was found (optional for API queries)
- `tool_calls` (array): All tool calls made during the loop

## System Prompt Strategy

The system prompt guides the LLM on tool selection:

1. **Wiki questions** (documentation, how-to guides, workflows): Use `list_files` and `read_file` on `wiki/` directory
2. **System facts** (framework, ports, status codes): Use `read_file` on source code in `backend/`
3. **Data queries** (item counts, scores, analytics): Use `query_api` to query backend
4. **Bug diagnosis**: Combine `query_api` (to see errors) with `read_file` (to check source code)

## Security

- Path traversal is blocked (no `../` in paths)
- Only files within the project directory can be accessed
- Maximum 10 tool calls prevents infinite loops
- API key is read from environment, not hardcoded

## Running the Agent

```bash
uv run agent.py "How many items are in the database?"
uv run agent.py "What framework does the backend use?"
uv run agent.py "How do you resolve a merge conflict?"
```

## Configuration

Create `.env.agent.secret` with LLM credentials:

```
LLM_API_KEY=your-llm-api-key
LLM_API_BASE=http://your-vm-ip:port/v1
LLM_MODEL=qwen3-coder-plus
```

Create `.env.docker.secret` with backend credentials:

```
LMS_API_KEY=your-backend-api-key
```

## Lessons Learned from Benchmark

### Initial Failures

1. **Agent didn't use query_api for data questions**: The system prompt was too focused on wiki files. Fixed by explicitly telling the LLM when to use each tool.

2. **API authentication errors**: Initially forgot to send the `X-API-Key` header. Added proper authentication.

3. **Source field missing for wiki answers**: Updated the system prompt to emphasize including source references.

### Iteration Strategy

1. Run `run_eval.py` to identify failures
2. Check which tool was used (or not used)
3. Adjust system prompt to clarify tool selection
4. Re-run and verify fix
5. Repeat until all questions pass

## Final Evaluation Score

After iteration, the agent passes all 10 local benchmark questions covering:
- Wiki lookup (documentation questions)
- System facts (framework, ports)
- Data queries (item counts, analytics)
- Bug diagnosis (API errors + source code)
- Reasoning (multi-step tool chaining)
