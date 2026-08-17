"""
escalation_node.py — Escalation Node (Phase 1 stub; full implementation in Phase 5).
On retries exhausted, exposes audit_history + escalation_reason via FastAPI endpoint
for manual human pass/fail input.
"""
import logging

from backend.state import AgentState

logger = logging.getLogger(__name__)


def escalation_node(state: AgentState) -> AgentState:
    """
    Phase 1: simple escalation — marks task as escalated and sets a reason.
    Phase 5: will expose a FastAPI endpoint for manual human decision.
    """
    audit_history = state["audit_history"]
    last_verdict = audit_history[-1] if audit_history else None

    reason = (
        f"Maximum retries ({state['max_retries']}) exhausted. "
        f"Last critique: {last_verdict.critique[:300] if last_verdict else 'N/A'}"
    )

    logger.warning(f"escalation_node: task escalated. {reason[:100]}")

    return {
        **state,
        "final_status": "escalated",
        "escalation_reason": reason,
    }
