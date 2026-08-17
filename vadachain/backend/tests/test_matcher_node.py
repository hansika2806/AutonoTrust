"""
test_matcher_node.py — Unit tests for the Matcher node (Phase 1 mocked version).
"""
import pytest
from backend.state import AgentState, TaskSpec
from backend.nodes.matcher_node import matcher_node
import time


def _make_state() -> AgentState:
    return {
        "raw_request": "write fib function",
        "task_spec": TaskSpec(
            task_id="match-test-001",
            description="Write a Python function fib(n)",
            acceptance_criteria=["fib(0) == 0"],
            budget=0.5,
            task_type="code",
            deadline_unix=int(time.time()) + 3600,
        ),
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


def test_matcher_returns_two_candidates():
    state = _make_state()
    result = matcher_node(state)
    assert len(result["candidate_executors"]) == 2


def test_matcher_picks_highest_success_rate():
    state = _make_state()
    result = matcher_node(state)
    # Should pick executor with 0.85 success rate (agent-001)
    assert result["chosen_executor"] == "executor-agent-001"


def test_matcher_sets_chosen_executor():
    state = _make_state()
    result = matcher_node(state)
    assert result["chosen_executor"] is not None
    assert isinstance(result["chosen_executor"], str)


def test_matcher_all_candidates_have_code_exec_skill():
    state = _make_state()
    result = matcher_node(state)
    for executor in result["candidate_executors"]:
        assert "code_exec" in executor.skills
