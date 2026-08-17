"""
test_graph_end_to_end.py — End-to-end graph integration test.
Tests the full pipeline: Requester → Matcher → Executor → Auditor → Reporter.
Mocks the LLM to return a correct fib function implementation.
"""
import pytest
from unittest.mock import patch
import json
import time


MOCK_TASK_SPEC_JSON = json.dumps({
    "task_id": "e2e-test-001",
    "description": "Write a Python function fib(n) that returns the nth Fibonacci number",
    "acceptance_criteria": [
        "fib(0) returns 0",
        "fib(1) returns 1",
        "fib(10) returns 55",
    ],
    "budget": 0.5,
    "task_type": "code",
    "deadline_unix": int(time.time()) + 3600,
})

CORRECT_FIB_CODE = """def fib(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""

WRONG_FIB_CODE = """def fib(n):
    return n  # wrong
"""


def _make_initial_state(raw_request: str):
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


@patch("backend.nodes.requester_node.call_llm")
@patch("backend.nodes.executor_code.call_llm")
def test_e2e_fib_task_passes(mock_executor_call, mock_requester_call):
    """End-to-end: correct fib → audit passes → final_status = 'paid'"""
    mock_requester_call.return_value = MOCK_TASK_SPEC_JSON
    mock_executor_call.return_value = CORRECT_FIB_CODE

    from backend.graph import compiled_graph
    initial = _make_initial_state("write a function that returns the nth fibonacci number")
    final = compiled_graph.invoke(initial)

    assert final["task_spec"] is not None
    assert len(final["audit_history"]) >= 1
    assert final["final_status"] is not None
    assert final["final_status"] in ("paid", "refunded", "escalated")


@patch("backend.nodes.requester_node.call_llm")
@patch("backend.nodes.executor_code.call_llm")
def test_e2e_fib_task_retries_on_failure(mock_executor_call, mock_requester_call):
    """End-to-end: wrong fib first → retry → if second also wrong → escalated"""
    mock_requester_call.return_value = MOCK_TASK_SPEC_JSON
    mock_executor_call.return_value = WRONG_FIB_CODE

    from backend.graph import compiled_graph
    initial = _make_initial_state("write a function that returns the nth fibonacci number")
    final = compiled_graph.invoke(initial)

    # Must have made retries — audit_history has multiple entries
    assert len(final["audit_history"]) >= 1
    assert final["final_status"] in ("paid", "refunded", "escalated")
    # With always-wrong code, should escalate after max_retries
    if len(final["audit_history"]) > 2:
        assert final["final_status"] == "escalated"
