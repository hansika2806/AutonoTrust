"""
e2e_amoy_test.py — One-shot end-to-end pipeline test against real Amoy chain.
Runs a fib(n) task through the full LangGraph pipeline, prints every tx hash.
Usage: .venv\Scripts\python scripts/e2e_amoy_test.py
"""
import sys
import os
import logging

# Make sure we can import from the backend package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("e2e_amoy_test")

from backend.graph import compiled_graph
from backend.state import AgentState

AMOY_EXPLORER = "https://amoy.polygonscan.com/tx/"

def main():
    logger.info("=== VadaChain Amoy End-to-End Test ===")

    initial_state: AgentState = {
        "raw_request": "write a Python function is_valid_email(s) that returns True if the input string is a properly formatted email address, False otherwise.",
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

    logger.info("Invoking graph pipeline...")
    final_state = compiled_graph.invoke(initial_state)

    print("\n" + "=" * 65)
    print("  VadaChain Pipeline — RESULTS")
    print("=" * 65)
    print(f"  Task ID:        {final_state['task_spec'].task_id if final_state.get('task_spec') else 'N/A'}")
    print(f"  Task Type:      {final_state['task_spec'].task_type if final_state.get('task_spec') else 'N/A'}")
    print(f"  Budget Locked:  {final_state['task_spec'].budget} POL" if final_state.get('task_spec') else "  Budget Locked:  N/A")
    print(f"  Chosen Executor:{final_state.get('chosen_executor', 'N/A')}")
    print(f"  Retries Used:   {final_state.get('retry_count', 0)}")
    print(f"  Final Status:   {final_state.get('final_status', 'N/A').upper()}")
    print()

    # Transaction hashes
    deploy_tx = None  # Deploy tx is separate from the pipeline
    lock_tx   = final_state.get("escrow_tx_hash")
    release_tx = final_state.get("reclaim_tx_hash")

    print("  Transaction Hashes:")
    if lock_tx:
        print(f"    [lockPayment]     {lock_tx}")
        if not lock_tx.startswith("0xMock"):
            print(f"    Explorer:         {AMOY_EXPLORER}{lock_tx}")
    else:
        print("    [lockPayment]     NOT FOUND (escrow not triggered)")

    if release_tx:
        verdict_type = "submitVerdict(PASS)" if final_state.get("final_status") == "paid" else "submitVerdict(FAIL/ESCALATE)"
        print(f"    [{verdict_type}] {release_tx}")
        if not release_tx.startswith("0xMock"):
            print(f"    Explorer:         {AMOY_EXPLORER}{release_tx}")
    else:
        print("    [submitVerdict]   NOT FOUND (escalated or not reached)")

    print()
    print("  Audit Verdicts:")
    for i, v in enumerate(final_state.get("audit_history", []), 1):
        status = "PASS" if v.passed else "FAIL"
        print(f"    Attempt {i}: [{status}] confidence={v.confidence:.0%}")

    print()
    print("  Executor Output (first 500 chars):")
    output = final_state.get("executor_output", "")
    print(f"    {output[:500]}")
    print("=" * 65)

    # Final verdict
    if lock_tx and not lock_tx.startswith("0xMock") and release_tx and not release_tx.startswith("0xMock"):
        print("\n  [OK] REAL AMOY TRANSACTIONS CONFIRMED. Paste hashes above into Polygonscan!")
    elif lock_tx and lock_tx.startswith("0xMock"):
        print("\n  [WARN] MOCKED TX HASHES -- contract call failed. Check .env and deployed_address.txt.")
    else:
        print("\n  [WARN] Task may have been escalated -- check escrow_reason above.")

if __name__ == "__main__":
    main()
