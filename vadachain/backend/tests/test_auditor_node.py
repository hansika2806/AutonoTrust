"""
test_auditor_node.py — Unit tests for the Auditor node.
"""
import pytest
import time

from backend.state import AgentState, TaskSpec
from backend.nodes.auditor_node import auditor_node


def _make_state(code: str, description: str = "Write a Python function fib(n)") -> AgentState:
    return {
        "raw_request": "fib request",
        "task_spec": TaskSpec(
            task_id="audit-test-001",
            description=description,
            acceptance_criteria=["fib(0) == 0"],
            budget=0.5,
            task_type="code",
            deadline_unix=int(time.time()) + 3600,
        ),
        "candidate_executors": [],
        "chosen_executor": "exec-001",
        "executor_output": code,
        "audit_history": [],
        "retry_count": 0,
        "max_retries": 2,
        "escrow_tx_hash": None,
        "reclaim_tx_hash": None,
        "reputation_tx_hash": None,
        "final_status": None,
        "escalation_reason": None,
    }


CORRECT_FIB = """
def fib(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""

WRONG_FIB = """
def fib(n):
    return n  # Wrong implementation
"""


def test_auditor_passes_correct_fib():
    state = _make_state(CORRECT_FIB)
    result = auditor_node(state)
    assert len(result["audit_history"]) == 1
    verdict = result["audit_history"][0]
    assert verdict.passed is True
    assert verdict.confidence == 1.0
    assert verdict.num_tests_passed if hasattr(verdict, 'num_tests_passed') else True


def test_auditor_fails_wrong_fib():
    state = _make_state(WRONG_FIB)
    result = auditor_node(state)
    assert len(result["audit_history"]) == 1
    verdict = result["audit_history"][0]
    assert verdict.passed is False
    assert verdict.confidence < 1.0


def test_auditor_handles_empty_output():
    state = _make_state("")
    result = auditor_node(state)
    assert len(result["audit_history"]) == 1
    verdict = result["audit_history"][0]
    assert verdict.passed is False


def test_auditor_appends_to_existing_history():
    from backend.state import AuditVerdict
    existing_verdict = AuditVerdict(
        passed=False, confidence=0.2, critique="Previous failure", retrieved_precedents=[]
    )
    state = _make_state(CORRECT_FIB)
    state["audit_history"] = [existing_verdict]
    result = auditor_node(state)
    assert len(result["audit_history"]) == 2
    assert result["audit_history"][-1].passed is True


CORRECT_EMAIL = """
import re

def is_valid_email(s):
    if not isinstance(s, str) or not s:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, s))
"""

def test_auditor_passes_correct_email():
    state = _make_state(CORRECT_EMAIL, description="write a Python function is_valid_email(s)")
    result = auditor_node(state)
    assert len(result["audit_history"]) == 1
    verdict = result["audit_history"][0]
    assert verdict.passed is True
    assert verdict.confidence == 1.0

