"""Regression test for agent.py CLI."""

import json
import subprocess
from pathlib import Path


def _run_agent(question: str) -> dict:
    """Helper to run agent.py and parse output."""
    # Project root is 2 levels up from tests/test_agent.py
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        ["uv", "run", str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=project_root,
    )

    assert result.returncode == 0, f"agent.py failed with: {result.stderr}"

    output = result.stdout.strip()
    return json.loads(output)


def test_agent_outputs_valid_json_with_required_fields() -> None:
    """Test that agent.py outputs valid JSON with required fields."""
    data = _run_agent("What is 2+2?")

    assert "answer" in data, "Missing 'answer' field in output JSON"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output JSON"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be an array"


def test_documentation_agent_uses_read_file_tool() -> None:
    """Test that agent uses read_file tool for documentation questions."""
    data = _run_agent("How do you resolve a merge conflict?")

    assert "answer" in data, "Missing 'answer' field"
    assert "source" in data, "Missing 'source' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"

    # Check that read_file was used
    tool_names = [tc.get("tool") for tc in data["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file tool to be called"

    # Check that source references a wiki git-related file
    assert "wiki/git" in data["source"], \
        f"Expected source to reference wiki/git*.md, got: {data['source']}"


def test_documentation_agent_uses_list_files_tool() -> None:
    """Test that agent uses list_files tool for directory questions."""
    data = _run_agent("What files are in the wiki?")

    assert "answer" in data, "Missing 'answer' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"

    # Check that list_files was used
    tool_names = [tc.get("tool") for tc in data["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files tool to be called"


def test_system_agent_uses_read_file_for_framework_question() -> None:
    """Test that agent uses read_file to find framework info in source code."""
    data = _run_agent("What framework does the backend use?")

    assert "answer" in data, "Missing 'answer' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"

    # Check that read_file was used to inspect source code
    tool_names = [tc.get("tool") for tc in data["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file tool to be called"


def test_system_agent_uses_query_api_for_data_question() -> None:
    """Test that agent uses query_api to get data from backend."""
    data = _run_agent("How many items are in the database?")

    assert "answer" in data, "Missing 'answer' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"

    # Check that query_api was used
    tool_names = [tc.get("tool") for tc in data["tool_calls"]]
    assert "query_api" in tool_names, "Expected query_api tool to be called"


def test_system_agent_uses_query_api_for_http_status_code() -> None:
    """Test that agent uses query_api to find HTTP status codes."""
    data = _run_agent(
        "What HTTP status code does the API return when you request /items/ "
        "without sending an authentication header?"
    )

    assert "answer" in data, "Missing 'answer' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"

    # Check that query_api was used
    tool_names = [tc.get("tool") for tc in data["tool_calls"]]
    assert "query_api" in tool_names, "Expected query_api tool to be called"

    # Check that the answer mentions 401 or Unauthorized
    answer_lower = data["answer"].lower()
    assert "401" in answer_lower or "unauthorized" in answer_lower, \
        f"Expected answer to mention 401 Unauthorized, got: {data['answer']}"


def test_system_agent_chains_tools_for_bug_diagnosis() -> None:
    """Test that agent chains query_api and read_file for bug diagnosis."""
    data = _run_agent(
        "The /analytics/top-learners endpoint crashes for some labs. "
        "Query it, find the error, and read the source code to explain what went wrong."
    )

    assert "answer" in data, "Missing 'answer' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"

    # Check that both query_api and read_file were used
    tool_names = [tc.get("tool") for tc in data["tool_calls"]]
    assert "query_api" in tool_names, "Expected query_api tool to be called"
    assert "read_file" in tool_names, "Expected read_file tool to be called"

    # Check that the answer mentions the bug (None/null comparison issue)
    answer_lower = data["answer"].lower()
    assert any(kw in answer_lower for kw in ["none", "null", "sorting", "compare"]), \
        f"Expected answer to mention None/null or sorting issue, got: {data['answer']}"
