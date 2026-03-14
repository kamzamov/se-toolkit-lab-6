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

## Benchmark Results

### Initial Score
- **First run**: 3/10 passed
- **Issues identified**:
  1. Agent returned double-encoded JSON in answer field
  2. Backend was not running (docker compose not started)
  3. LLM returned multiple tool calls in single response
  4. LLM included conversational text before JSON
  5. LLM used `body` parameter for GET requests, creating malformed JSON

### Iterations

**Iteration 1**: Fixed JSON parser to handle balanced braces with string escaping
- Score: 6/10 passed
- Remaining issues: LLM still returning malformed JSON with nested quotes

**Iteration 2**: Updated system prompt to:
- Forbid text outside JSON
- Require ONE tool call at a time
- Use query parameters instead of body for GET requests
- Score: 8/10 passed

**Iteration 3**: Fixed escape handling in JSON parser
- Score: 10/10 passed

### Final Score
**10/10 PASSED** on all local benchmark questions

### Test Results
All 7 regression tests pass:
- `test_agent_outputs_valid_json_with_required_fields`
- `test_documentation_agent_uses_read_file_tool`
- `test_documentation_agent_uses_list_files_tool`
- `test_system_agent_uses_read_file_for_framework_question`
- `test_system_agent_uses_query_api_for_data_question`
- `test_system_agent_uses_query_api_for_http_status_code`
- `test_system_agent_chains_tools_for_bug_diagnosis`

### Key Lessons Learned

1. **LLM output is non-deterministic**: The same question can produce different output formats. The system prompt must be very explicit about expected format.

2. **JSON parsing is fragile**: When the LLM includes nested JSON strings (like `body: "{\"key\": \"value\"}"`), standard parsers fail. A custom balanced-brace parser with string awareness is needed.

3. **Query parameters vs body**: For GET requests, instructing the LLM to use query parameters in the path (e.g., `/endpoint?param=value`) instead of a body field avoids JSON escaping issues.

4. **Tool chaining requires patience**: The LLM might try to make multiple tool calls in one response. The system must enforce one-at-a-time execution.

5. **Backend must be running**: The `query_api` tool requires the backend to be running. Make sure to run `docker compose up` before testing.
