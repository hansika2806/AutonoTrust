"""
test_executor_code.py — Unit tests for the code executor node.
"""
import pytest
from unittest.mock import patch

from backend.state import AgentState, TaskSpec, AuditVerdict
from backend.nodes.executor_code import executor_code_node
import time


def _make_state_with_task(retry_count: int = 0, audit_history=None) -> AgentState:
    return {
        "raw_request": "write fib function",
        "task_spec": TaskSpec(
            task_id="test-task-001",
            description="Write a Python function fib(n) that returns the nth Fibonacci number",
            acceptance_criteria=["fib(0) == 0", "fib(1) == 1", "fib(10) == 55"],
            budget=0.5,
            task_type="code",
            deadline_unix=int(time.time()) + 3600,
        ),
        "candidate_executors": [],
        "chosen_executor": "executor-001",
        "executor_output": None,
        "audit_history": audit_history or [],
        "retry_count": retry_count,
        "max_retries": 2,
        "escrow_tx_hash": None,
        "reclaim_tx_hash": None,
        "reputation_tx_hash": None,
        "final_status": None,
        "escalation_reason": None,
    }


MOCK_CODE = """def fib(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)
"""


@patch("backend.nodes.executor_code.call_llm", return_value=MOCK_CODE)
def test_executor_code_generates_output(mock_llm):
    state = _make_state_with_task()
    result = executor_code_node(state)
    assert result["executor_output"] is not None
    assert "def fib" in result["executor_output"]


@patch("backend.nodes.executor_code.call_llm", return_value=MOCK_CODE)
def test_executor_code_strips_fences(mock_llm):
    fenced = f"```python\n{MOCK_CODE}\n```"
    with patch("backend.nodes.executor_code.call_llm", return_value=fenced):
        state = _make_state_with_task()
        result = executor_code_node(state)
        assert "```" not in result["executor_output"]


@patch("backend.nodes.executor_code.call_llm", return_value=MOCK_CODE)
def test_executor_code_injects_critique_on_retry(mock_llm):
    """Verify critique is injected into prompt on retry (Reflexion)."""
    critique_text = "fib(0) returned 1 instead of 0"
    verdict = AuditVerdict(
        passed=False,
        confidence=0.4,
        critique=critique_text,
        retrieved_precedents=[],
    )
    state = _make_state_with_task(retry_count=1, audit_history=[verdict])
    
    with patch("backend.nodes.executor_code.call_llm") as mock:
        mock.return_value = MOCK_CODE
        executor_code_node(state)
        # Verify the critique was included in the messages
        call_messages = mock.call_args[0][0]
        user_message = next(m for m in call_messages if m["role"] == "user")
        assert critique_text in user_message["content"]
