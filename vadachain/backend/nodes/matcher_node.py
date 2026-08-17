"""
matcher_node.py — Matcher Agent.
Phase 1-3: hardcoded mock executor profiles, on-chain reputation lookup.
Phase 4: adds RAG retrieval of top-3 similar task precedents for context.
"""
import logging

from backend.state import AgentState, ExecutorProfile
from backend.config import EXECUTOR_1_ADDRESS, EXECUTOR_2_ADDRESS
from backend.tools.vector_store import retrieve_task_precedents

logger = logging.getLogger(__name__)

# Hardcoded mock executor profiles (Phase 1-3 base)
_MOCK_EXECUTORS: list[ExecutorProfile] = [
    ExecutorProfile(
        agent_id="executor-agent-001",
        wallet_address=EXECUTOR_1_ADDRESS or "0xMockExecutor1Address",
        skills=["code_exec"],
        past_success_rate=0.85,
        tasks_completed=42,
    ),
    ExecutorProfile(
        agent_id="executor-agent-002",
        wallet_address=EXECUTOR_2_ADDRESS or "0xMockExecutor2Address",
        skills=["code_exec"],
        past_success_rate=0.72,
        tasks_completed=31,
    ),
]


def matcher_node(state: AgentState) -> AgentState:
    """
    Phase 4: retrieves top-3 similar task precedents from ChromaDB,
    fetches on-chain reputation rates from contract, picks executor with
    highest success rate.
    """
    task_spec = state["task_spec"]
    logger.info(f"matcher_node: matching executors for task_id={task_spec.task_id}")

    # --- Phase 4: RAG retrieval of similar precedents ---
    precedents = retrieve_task_precedents(query=task_spec.description, top_k=3)
    if precedents:
        logger.info(f"matcher_node: retrieved {len(precedents)} similar task precedents from memory")
        for i, p in enumerate(precedents[:3], 1):
            logger.info(f"  Precedent {i}: {p[:120]}")
    else:
        logger.info("matcher_node: no similar precedents found (fresh start)")

    candidates = _MOCK_EXECUTORS.copy()

    from backend.chain.contract_client import get_success_rate

    # Update candidate success rates from contract if possible
    updated_candidates = []
    for candidate in candidates:
        try:
            rate_pct = get_success_rate(candidate.wallet_address)
            candidate_dict = candidate.model_dump()
            candidate_dict["past_success_rate"] = rate_pct / 100.0
            updated_candidates.append(ExecutorProfile(**candidate_dict))
            logger.info(f"matcher_node: fetched on-chain reputation for {candidate.agent_id}: {rate_pct}%")
        except Exception as e:
            logger.warning(f"matcher_node: could not fetch reputation for {candidate.agent_id} from contract ({e}). Using default: {candidate.past_success_rate}")
            updated_candidates.append(candidate)

    # Pick highest success rate
    best = max(updated_candidates, key=lambda e: e.past_success_rate)
    logger.info(
        f"matcher_node: chose executor={best.agent_id} "
        f"(success_rate={best.past_success_rate})"
    )

    return {
        **state,
        "candidate_executors": updated_candidates,
        "chosen_executor": best.agent_id,
    }
