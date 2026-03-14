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
  - `path` (string) - API endpoint path with optional query parameters (e.g., `/items/`, `/analytics/completion-rate?lab=lab-99`)
  - `body` (string, optional) - JSON request body for POST/PUT requests only
  - `use_auth` (boolean) - Whether to include authentication (default: true)
- **Returns**: JSON string with `status_code` and `body`
- **Authentication**: Uses `LMS_API_KEY` from environment variables, sent as `Authorization: Bearer` header
- **Use cases**: Item counts, analytics data, scores, system status, HTTP error codes

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
5. **Final answer**: When LLM returns `final_answer`, extract answer and source
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
5. **Architecture questions** (request flow, docker): Read relevant config files and synthesize an answer

The system prompt explicitly instructs the LLM to:
- Make ONLY ONE tool call at a time
- Use query parameters in the path for GET requests (not the body field)
- Respond with ONLY valid JSON, no explanatory text
- Provide a final answer after gathering enough information

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
uv run agent.py "The /analytics/top-learners endpoint crashes. Explain why."
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

1. **Malformed JSON from LLM**: The LLM sometimes returned multiple tool calls in a single response or included explanatory text before the JSON. This broke the parser. Fixed by:
   - Updating the system prompt to explicitly forbid text outside JSON
   - Improving the JSON parser to handle nested escaped strings properly
   - Instructing the LLM to use query parameters instead of body for GET requests

2. **Agent didn't use query_api for data questions**: The system prompt was too focused on wiki files. Fixed by explicitly telling the LLM when to use each tool.

3. **API authentication errors**: Initially the authentication header wasn't being sent correctly. Added proper `Authorization: Bearer` header.

4. **LLM stopped after first tool call**: The LLM would sometimes make one tool call and then stop without providing a final answer. Fixed by:
   - Clarifying in the system prompt that the LLM should continue until it has enough information
   - Increasing the maximum tool calls limit
   - Making the loop continue until a `final_answer` is received

5. **Nested JSON in body parameter**: When the LLM used the `body` parameter for GET requests, it created malformed JSON with escaped quotes. Fixed by instructing the LLM to use query parameters in the path instead.

### Iteration Strategy

1. Run `run_eval.py` to identify failures
2. Check which tool was used (or not used)
3. Check if the LLM output is valid JSON
4. Adjust system prompt to clarify tool selection and output format
5. Improve JSON parser to handle edge cases
6. Re-run and verify fix
7. Repeat until all questions pass

## Final Evaluation Score

After iteration, the agent passes all 10 local benchmark questions covering:
- Wiki lookup (documentation questions about Git workflow and SSH)
- System facts (FastAPI framework, port numbers)
- Data queries (item counts in database)
- HTTP status codes (401 Unauthorized without auth)
- Bug diagnosis (division by zero in completion-rate, None comparison in top-learners)
- Architecture reasoning (HTTP request journey through docker-compose services)
- Code analysis (ETL pipeline idempotency)

The agent successfully chains multiple tools together, reading API errors and then examining source code to diagnose bugs. It properly handles query parameters for GET requests and uses authentication when required.
