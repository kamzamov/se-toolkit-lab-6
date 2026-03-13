# Agent Architecture

## Overview

This agent is a CLI tool that answers questions by reading project documentation. It uses an agentic loop to discover and read wiki files, then synthesizes answers with source references.

## LLM Provider

- **Provider**: Qwen Code API (self-hosted on VM)
- **Model**: `qwen3-coder-plus`
- **Endpoint**: OpenAI-compatible chat completions API

## Tools

The agent has two tools for navigating the project repository:

### `read_file`

Reads a file from the project repository.

- **Parameters**: `path` (string) - relative path from project root
- **Returns**: File contents as string, or error message
- **Security**: Blocks paths with `../` to prevent directory traversal

### `list_files`

Lists files and directories at a given path.

- **Parameters**: `path` (string) - relative directory path from project root
- **Returns**: Newline-separated listing of entries, or error message
- **Security**: Blocks paths with `../` to prevent directory traversal

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
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

- `answer` (string): The LLM's final answer
- `source` (string): File path where the answer was found
- `tool_calls` (array): All tool calls made during the loop

## System Prompt Strategy

The system prompt instructs the LLM to:
1. Use `list_files` to explore the wiki directory structure
2. Use `read_file` to read relevant documentation files
3. Extract source references from files it reads
4. Include the source path in the final answer
5. Respond with ONLY valid JSON

## Security

- Path traversal is blocked (no `../` in paths)
- Only files within the project directory can be accessed
- Maximum 10 tool calls prevents infinite loops

## Running the Agent

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

## Configuration

Create `.env.agent.secret` with:

```
LLM_API_KEY=your-api-key
LLM_API_BASE=http://your-vm-ip:port/v1
LLM_MODEL=qwen3-coder-plus
```
