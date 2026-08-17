"""
test_requester_node.py — Unit tests for the Requester Agent node.
"""
import pytest
from unittest.mock import patch

from backend.state import AgentState
from backend.nodes.requester_node import requester_node


def _make_initial_state(raw_request: str) -> AgentState:
    return {
        "raw_request": raw_request,
        "task_spec": None,
        "candidate_executors": [],
        "chosen_executor": None,
        "executor_output": None,
        "audit_history": [],
        "retry_count": 0,
        "max_retries": 2,
        "escrow_tx_hash": None,
        "reclaim_tx_hash": None,
        "reputation_tx_hash": None,
        "final_status": None,
        "escalation_reason": None,
    }


MOCK_LLM_RESPONSE = '''{
  "task_id": "test-uuid-1234",
  "description": "Write a Python function fib(n) that returns the nth Fibonacci number",
  "acceptance_criteria": [
    "fib(0) returns 0",
    "fib(1) returns 1",
    "fib(2) returns 1",
    "fib(10) returns 55",
    "fib(20) returns 6765"
  ],
  "budget": 0.5,
  "task_type": "code",
  "deadline_unix": 9999999999
}'''


@patch("backend.nodes.requester_node.call_llm", return_value=MOCK_LLM_RESPONSE)
def test_requester_node_creates_task_spec(mock_llm):
    state = _make_initial_state("write a function that returns the nth fibonacci number")
    result = requester_node(state)

    assert result["task_spec"] is not None
    assert result["task_spec"].task_id == "test-uuid-1234"
    assert result["task_spec"].task_type == "code"
    assert len(result["task_spec"].acceptance_criteria) == 5
    assert result["max_retries"] == 2
    assert result["retry_count"] == 0
    assert result["audit_history"] == []


@patch("backend.nodes.requester_node.call_llm", return_value=MOCK_LLM_RESPONSE)
def test_requester_node_strips_markdown_fences(mock_llm):
    """Test that LLM responses wrapped in ```json fences are handled."""
    fenced_response = f"```json\n{MOCK_LLM_RESPONSE}\n```"
    with patch("backend.nodes.requester_node.call_llm", return_value=fenced_response):
        state = _make_initial_state("write fibonacci function")
        result = requester_node(state)
        assert result["task_spec"] is not None
        assert result["task_spec"].task_type == "code"
