# Task 2 Plan: The Documentation Agent

## LLM Provider
- Provider: Qwen Code API (self-hosted on VM)
- Model: qwen3-coder-plus
- Endpoint: http://10.93.25.19:42005/v1

## Tool Definitions

### read_file
- **Purpose**: Read file contents from the project repository
- **Parameters**: `path` (string) - relative path from project root
- **Security**: Block paths with `../` to prevent directory traversal
- **Returns**: File contents as string or error message

### list_files
- **Purpose**: List files and directories at a given path
- **Parameters**: `path` (string) - relative directory path from project root
- **Security**: Block paths with `../` to prevent directory traversal
- **Returns**: Newline-separated listing of entries

## Agentic Loop Design

1. Send user question + system prompt to LLM
2. Parse LLM response for JSON tool calls or final answer
3. If tool call → execute tool, append result to messages, repeat
4. If final answer → extract answer and source, return JSON
5. Maximum 10 tool calls per question (safety limit)
6. Track all tool calls with args and results for output

## System Prompt Strategy

Tell the LLM to:
1. Use `list_files` to discover wiki directory structure
2. Use `read_file` to read relevant wiki files
3. Extract the source path from files it reads
4. Include source reference in final answer (e.g., `wiki/git-workflow.md#section`)
5. Respond with ONLY valid JSON

## Error Handling

- File not found → return error message as tool result
- Path traversal attempt → block and return error
- LLM API errors → exit with error code 1
- Timeout >60s → handled by requests library

## Testing

- Test 1: Question about merge conflicts → expects `read_file` tool, `wiki/git*.md` in source
- Test 2: Question about wiki files → expects `list_files` tool
