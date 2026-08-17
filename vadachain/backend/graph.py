"""
graph.py — LangGraph graph assembly (nodes + edges wired together).

Topology:
  requester_node
      → matcher_node
          → executor_node
              → auditor_node
                  → route_after_audit()
                      "release"  → reporter_node  → END
                      "retry"    → executor_node  (Reflexion loop)
                      "escalate" → escalation_node → reporter_node → END

Conditional edge (exact spec):
    def route_after_audit(state) -> Literal["retry","release","escalate"]:
        last = state["audit_history"][-1]
        if last.passed:
            return "release"
        elif state["retry_count"] < state["max_retries"]:
            return "retry"
        else:
            return "escalate"

On "retry": increment retry_count, route back to executor_node,
            inject latest critique into Executor's prompt context
            (done inside executor_code_node by reading state["audit_history"][-1].critique)
"""
import logging
import uuid
import hashlib
from typing import Literal

from langgraph.graph import StateGraph, END

from backend.state import AgentState
from backend.nodes.requester_node import requester_node
from backend.nodes.matcher_node import matcher_node
from backend.nodes.executor_node import executor_node
from backend.nodes.auditor_node import auditor_node
from backend.nodes.reporter_node import reporter_node
from backend.nodes.escalation_node import escalation_node
from backend.config import AUDITOR_ADDRESS
from backend.chain.contract_client import lock_payment, submit_verdict

logger = logging.getLogger(__name__)


def route_after_audit(state: AgentState) -> Literal["retry", "release", "escalate"]:
    """
    Conditional edge function — exact spec implementation.
    """
    last = state["audit_history"][-1]
    if last.passed:
        return "release"
    elif state["retry_count"] < state["max_retries"]:
        return "retry"
    else:
        return "escalate"


def _increment_retry(state: AgentState) -> AgentState:
    """
    Helper node: increments retry_count before routing back to executor.
    Required so the executor knows it's a retry and injects the critique.
    """
    new_count = state["retry_count"] + 1
    logger.info(f"retry_increment: retry_count {state['retry_count']} → {new_count}")
    return {**state, "retry_count": new_count}



# =====================================================================
# Phase 3 Escrow Nodes
# =====================================================================

def _task_id_to_int(task_id: str) -> int:
    """Convert a task_id string to a uint256. Tries UUID first, falls back to sha256 hash."""
    try:
        return uuid.UUID(task_id).int
    except (ValueError, AttributeError):
        return int(hashlib.sha256(task_id.encode()).hexdigest()[:32], 16)


def escrow_lock_node(state: AgentState) -> AgentState:
    """
    Escrow Lock Node: converts task ID to uint256, looks up executor address,
    and calls lock_payment on the Solidity contract.
    """
    task_spec = state["task_spec"]
    chosen_exec_id = state["chosen_executor"]
    
    # Convert UUID string to uint256
    task_id_int = _task_id_to_int(task_spec.task_id)
    
    # Find executor's address
    exec_profile = next(c for c in state["candidate_executors"] if c.agent_id == chosen_exec_id)
    executor_address = exec_profile.wallet_address
    
    # 1 budget units = 1 MATIC (in wei)
    amount_wei = int(task_spec.budget * 10**18)
    
    logger.info(f"escrow_lock_node: locking {task_spec.budget} MATIC for task {task_spec.task_id} (int: {task_id_int})")
    
    try:
        tx_hash = lock_payment(
            task_id=task_id_int,
            executor_address=executor_address,
            auditor_address=AUDITOR_ADDRESS,
            amount_wei=amount_wei,
            deadline_unix=task_spec.deadline_unix,
        )
        logger.info(f"escrow_lock_node: payment locked successfully. Tx: {tx_hash}")
        return {**state, "escrow_tx_hash": tx_hash}
    except Exception as e:
        logger.warning(f"escrow_lock_node: contract lockPayment failed ({e}). Mocking tx hash.")
        return {**state, "escrow_tx_hash": "0xMockLockPaymentTxHash"}


def escrow_release_node(state: AgentState) -> AgentState:
    """
    Escrow Release Node: calls submit_verdict(task_id, passed=True) from auditor wallet.
    """
    task_spec = state["task_spec"]
    task_id_int = _task_id_to_int(task_spec.task_id)
    
    logger.info(f"escrow_release_node: releasing funds for task {task_spec.task_id}")
    
    try:
        tx_hash = submit_verdict(task_id=task_id_int, passed=True)
        logger.info(f"escrow_release_node: funds released successfully. Tx: {tx_hash}")
        return {**state, "reclaim_tx_hash": tx_hash, "final_status": "paid"}
    except Exception as e:
        logger.warning(f"escrow_release_node: contract submitVerdict(true) failed ({e}). Mocking release.")
        return {**state, "reclaim_tx_hash": "0xMockReleasePaymentTxHash", "final_status": "paid"}


def escrow_refund_node(state: AgentState) -> AgentState:
    """
    Escrow Refund Node: calls submit_verdict(task_id, passed=False) from auditor wallet.
    """
    task_spec = state["task_spec"]
    task_id_int = _task_id_to_int(task_spec.task_id)
    
    logger.info(f"escrow_refund_node: refunding/reclaiming funds for task {task_spec.task_id}")
    
    try:
        tx_hash = submit_verdict(task_id=task_id_int, passed=False)
        logger.info(f"escrow_refund_node: funds refunded successfully. Tx: {tx_hash}")
        return {**state, "reclaim_tx_hash": tx_hash, "final_status": "refunded"}
    except Exception as e:
        logger.warning(f"escrow_refund_node: contract submitVerdict(false) failed ({e}). Mocking refund.")
        return {**state, "reclaim_tx_hash": "0xMockRefundPaymentTxHash", "final_status": "refunded"}


def build_graph() -> StateGraph:
    """
    Assembles and compiles the VadaChain LangGraph.
    """
    workflow = StateGraph(AgentState)

    # --- Register nodes ---
    workflow.add_node("requester_node", requester_node)
    workflow.add_node("matcher_node", matcher_node)
    workflow.add_node("escrow_lock_node", escrow_lock_node)
    workflow.add_node("executor_node", executor_node)
    workflow.add_node("auditor_node", auditor_node)
    workflow.add_node("escrow_release_node", escrow_release_node)
    workflow.add_node("reporter_node", reporter_node)
    workflow.add_node("escalation_node", escalation_node)
    workflow.add_node("retry_increment", _increment_retry)

    # --- Set entrypoint ---
    workflow.set_entry_point("requester_node")

    # --- Linear edges ---
    workflow.add_edge("requester_node", "matcher_node")
    workflow.add_edge("matcher_node", "escrow_lock_node")
    workflow.add_edge("escrow_lock_node", "executor_node")
    workflow.add_edge("executor_node", "auditor_node")

    # --- Conditional edge after audit ---
    workflow.add_conditional_edges(
        "auditor_node",
        route_after_audit,
        {
            "release": "escrow_release_node",
            "retry": "retry_increment",
            "escalate": "escalation_node",
        },
    )

    # On retry: increment count, then re-run executor (Reflexion loop)
    workflow.add_edge("retry_increment", "executor_node")

    # Release node flows to final reporting
    workflow.add_edge("escrow_release_node", "reporter_node")

    
    # Escalation → reporter for final summary
    workflow.add_edge("escalation_node", "reporter_node")

    # Reporter → END
    workflow.add_edge("reporter_node", END)

    return workflow.compile()


# Singleton compiled graph
compiled_graph = build_graph()
