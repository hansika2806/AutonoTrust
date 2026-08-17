"""
main.py — FastAPI entrypoint.
One endpoint: POST /run_task accepting {"raw_request": str},
invoking the compiled LangGraph graph, returning the full final AgentState as JSON.
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.graph import compiled_graph
from backend.state import AgentState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VadaChain API",
    description="Multi-agent AI system with blockchain escrow on Polygon Amoy",
    version="0.1.0",
)

# Allow frontend (Vite dev server + Vercel) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunTaskRequest(BaseModel):
    raw_request: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "VadaChain"}


@app.post("/run_task")
async def run_task(request: RunTaskRequest) -> dict:
    """
    Main endpoint: accepts a raw task request, runs the full LangGraph pipeline,
    returns the complete final AgentState as JSON.

    Example input:
        {"raw_request": "write a function that returns the nth fibonacci number"}

    Returns:
        Full AgentState including task_spec, audit_history, final_status, etc.
    """
    if not request.raw_request.strip():
        raise HTTPException(status_code=400, detail="raw_request cannot be empty")

    logger.info(f"POST /run_task — raw_request: {request.raw_request[:80]!r}")

    # Build initial state
    initial_state: AgentState = {
        "raw_request": request.raw_request,
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

    try:
        final_state = compiled_graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

    # Serialize (Pydantic models → dicts for JSON response)
    result = _serialize_state(final_state)

    if result.get("final_status") == "escalated":
        _register_escalation(result)

    logger.info(f"POST /run_task — completed, final_status={result.get('final_status')}")
    return result


def _serialize_state(state: AgentState) -> dict:
    """Convert AgentState (with Pydantic sub-objects) to a JSON-serializable dict."""
    result = {}
    for key, value in state.items():
        if hasattr(value, "model_dump"):
            result[key] = value.model_dump()
        elif isinstance(value, list):
            result[key] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in value
            ]
        else:
            result[key] = value
    return result


# =====================================================================
# Escalation Store (in-memory for Phase 5; swap for Redis/DB in prod)
# =====================================================================
_escalation_store: dict[str, dict] = {}


class EscalationResolution(BaseModel):
    decision: str  # "approve" | "reject"
    reviewer_note: str = ""


@app.get("/escalations")
async def list_escalations() -> dict:
    """List all pending escalated tasks."""
    return {"escalations": list(_escalation_store.values())}


@app.get("/escalations/{task_id}")
async def get_escalation(task_id: str) -> dict:
    """Get details of a specific escalated task."""
    if task_id not in _escalation_store:
        raise HTTPException(status_code=404, detail=f"Escalation not found: {task_id}")
    return _escalation_store[task_id]


@app.post("/escalations/{task_id}/resolve")
async def resolve_escalation(task_id: str, resolution: EscalationResolution) -> dict:
    """
    Human reviewer approves or rejects an escalated task.
    - approve → triggers escrow release (submit_verdict true)
    - reject  → triggers escrow refund (submit_verdict false)
    """
    if task_id not in _escalation_store:
        raise HTTPException(status_code=404, detail=f"Escalation not found: {task_id}")
    if resolution.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")

    escalation = _escalation_store[task_id]
    passed = resolution.decision == "approve"

    logger.info(f"POST /escalations/{task_id}/resolve — decision={resolution.decision}")

    try:
        import hashlib, uuid as _uuid
        try:
            task_id_int = _uuid.UUID(task_id).int
        except ValueError:
            task_id_int = int(hashlib.sha256(task_id.encode()).hexdigest()[:32], 16)

        from backend.chain.contract_client import submit_verdict
        tx_hash = submit_verdict(task_id=task_id_int, passed=passed)
    except Exception as e:
        logger.warning(f"resolve_escalation: contract call failed ({e})")
        tx_hash = "0xMockResolutionTxHash"

    _escalation_store[task_id]["resolved"] = True
    _escalation_store[task_id]["resolution"] = resolution.decision
    _escalation_store[task_id]["reviewer_note"] = resolution.reviewer_note
    _escalation_store[task_id]["resolution_tx_hash"] = tx_hash

    return {
        "task_id": task_id,
        "decision": resolution.decision,
        "tx_hash": tx_hash,
        "status": "paid" if passed else "refunded",
    }


def _register_escalation(state_dict: dict) -> None:
    """Called by /run_task when final_status == 'escalated'. Registers into store."""
    task_id = state_dict.get("task_spec", {}).get("task_id", "unknown")
    _escalation_store[task_id] = {
        "task_id": task_id,
        "description": state_dict.get("task_spec", {}).get("description", ""),
        "escalation_reason": state_dict.get("escalation_reason", ""),
        "audit_history": state_dict.get("audit_history", []),
        "resolved": False,
        "resolution": None,
        "resolution_tx_hash": None,
    }
    logger.info(f"Escalation registered for task_id={task_id}")

