"""Regression test for agent.py CLI."""

import json
import subprocess
from pathlib import Path


def _run_agent(question: str) -> dict:
    """Helper to run agent.py and parse output."""
    project_root = Path(__file__).parent.parent.parent.parent
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
