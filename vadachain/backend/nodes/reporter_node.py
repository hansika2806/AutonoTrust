"""
reporter_node.py — Reporter Agent.
Produces a final plain-text summary covering:
task description, chosen executor, number of attempts, final verdict,
and (in Phase 1) a placeholder "[escrow not yet implemented]" where the tx hash will go.
"""
import logging

from backend.state import AgentState
from backend.tools.vector_store import add_task_precedent

logger = logging.getLogger(__name__)


def reporter_node(state: AgentState) -> AgentState:
    """
    Produces a final human-readable summary of the completed task run.
    Sets final_status based on the last audit verdict.
    Phase 1: escrow_tx_hash is None — placeholder used in report.
    """
    task_spec = state["task_spec"]
    audit_history = state["audit_history"]
    chosen_executor = state.get("chosen_executor", "unknown")
    retry_count = state.get("retry_count", 0)
    escrow_tx_hash = state.get("escrow_tx_hash")
    final_status = state.get("final_status")

    last_verdict = audit_history[-1] if audit_history else None
    passed = last_verdict.passed if last_verdict else False

    # Determine final status if not already set (e.g., by escalation)
    if not final_status:
        final_status = "paid" if passed else "refunded"

    num_attempts = retry_count + 1  # retry_count is increments after first attempt

    tx_display = escrow_tx_hash if escrow_tx_hash else "[escrow not yet implemented]"

    report_lines = [
        "=" * 60,
        "VadaChain Task Report",
        "=" * 60,
        f"Task ID:           {task_spec.task_id}",
        f"Description:       {task_spec.description}",
        f"Task Type:         {task_spec.task_type}",
        f"Chosen Executor:   {chosen_executor}",
        f"Attempts Made:     {num_attempts}",
        f"Final Verdict:     {'PASS ✓' if passed else 'FAIL ✗'}",
        f"Final Status:      {final_status.upper()}",
        f"Escrow TX Hash:    {tx_display}",
        "=" * 60,
    ]

    if last_verdict:
        report_lines.append(f"Confidence:        {last_verdict.confidence:.1%}")
        report_lines.append(f"Critique:          {last_verdict.critique[:200]}")

    if len(audit_history) > 1:
        report_lines.append("\nAudit History:")
        for i, v in enumerate(audit_history, 1):
            status = "PASS" if v.passed else "FAIL"
            report_lines.append(
                f"  Attempt {i}: [{status}] confidence={v.confidence:.1%}"
            )

    report = "\n".join(report_lines)
    logger.info(f"reporter_node: final_status={final_status}, attempts={num_attempts}")

    # --- Phase 4: Write task outcome to ChromaDB for future RAG retrieval ---
    try:
        add_task_precedent(
            task_id=task_spec.task_id,
            description=task_spec.description,
            verdict_passed=passed,
            critique=last_verdict.critique if last_verdict else "No audit performed",
        )
        logger.info(f"reporter_node: task precedent written to memory (task_id={task_spec.task_id})")
    except Exception as e:
        logger.warning(f"reporter_node: could not write task precedent to memory ({e})")

    return {
        **state,
        "final_status": final_status,
        "executor_output": state.get("executor_output", ""),
    }
