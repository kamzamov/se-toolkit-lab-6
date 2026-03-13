# Task 3 Plan: The System Agent

## LLM Provider
- Provider: Qwen Code API (self-hosted on VM)
- Model: qwen3-coder-plus
- Endpoint: http://10.93.25.19:42005/v1

## New Tool: query_api

### Purpose
Query the deployed backend LMS API to get real-time data about items, analytics, and system status.

### Parameters
- `method` (string): HTTP method (GET, POST, etc.)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

### Authentication
- Use `LMS_API_KEY` from environment variables
- Send as `X-API-Key` header in requests

### Returns
JSON string with:
- `status_code`: HTTP status code
- `body`: Response body as JSON string

## Environment Variables

The agent must read all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

## System Prompt Strategy

Update the system prompt to guide the LLM on when to use each tool:

1. **Wiki questions** (documentation, how-to): Use `list_files` and `read_file`
2. **System facts** (framework, ports, status codes): Use `read_file` to check source code
3. **Data queries** (item count, scores, analytics): Use `query_api` to query backend
4. **Bug diagnosis**: Combine `query_api` (to see errors) with `read_file` (to check code)

## Implementation Steps

1. Add `LMS_API_KEY` and `AGENT_API_BASE_URL` to environment loading
2. Implement `query_api` tool with authentication
3. Add `query_api` to tool definitions
4. Update system prompt with tool selection guidance
5. Update `AGENT.md` with new architecture
6. Add 2 regression tests for system agent
7. Run `run_eval.py` and iterate until all 10 questions pass

## Testing

- Test 1: "What framework does the backend use?" → expects `read_file` tool
- Test 2: "How many items are in the database?" → expects `query_api` tool

## Benchmark Strategy

1. Run `run_eval.py` to see initial score
2. For each failure:
   - Check if correct tool was used
   - Check if tool arguments are correct
   - Adjust system prompt or tool descriptions
3. Iterate until 10/10 questions pass
