"""
requester_node.py — Requester Agent.
LLM call with structured output forcing a TaskSpec.
System prompt instructs: "Rewrite the user's request into a task with objective,
testable acceptance criteria. For coding tasks, acceptance criteria must be
phrased as things a test suite can check (e.g. 'function returns correct value
for n=0 through n=10'), never subjective language like 'good' or 'clean'."
Sets max_retries = 2 as default in this node when creating state.
"""
import json
import uuid
import time
import logging

from backend.state import AgentState, TaskSpec
from backend.tools.llm_client import call_llm
from backend.config import MAX_RETRIES

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Task Specification Agent. Your job is to rewrite a user's natural-language 
request into a precise, machine-verifiable task specification.

RULES:
- acceptance_criteria must ONLY contain things a unit-test suite can check objectively.
- Do NOT use subjective language like 'good', 'clean', 'readable', 'efficient'.
- For coding tasks: acceptance criteria must be function-level contracts (e.g., "function fib(n) returns 0 for n=0", "function fib(n) returns 1 for n=1").
- task_type must be exactly one of: "code", "research", "writing".
- budget is in USD (floating point). Use 0.02 as default if not specified.
- deadline_unix is seconds since epoch. Use now + 3600 if not specified.
- task_id must be a unique UUID string.

Respond ONLY with valid JSON matching this exact schema:
{
  "task_id": "<uuid>",
  "description": "<clear, one-sentence task description>",
  "acceptance_criteria": ["<criterion 1>", "<criterion 2>", ...],
  "budget": <float>,
  "task_type": "<code|research|writing>",
  "deadline_unix": <int>
}"""


def requester_node(state: AgentState) -> AgentState:
    """
    Converts raw_request into a structured TaskSpec via LLM.
    Sets max_retries default.
    """
    raw = state["raw_request"]
    logger.info(f"requester_node: processing request: {raw[:80]}...")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User request: {raw}"},
    ]

    raw_json = call_llm(messages, temperature=0.1, max_tokens=1024)

    # Strip markdown fences if LLM wraps in ```json ... ```
    raw_json = raw_json.strip()
    if raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1]
        if raw_json.startswith("json"):
            raw_json = raw_json[4:]
        raw_json = raw_json.strip()

    data = json.loads(raw_json)

    # Fill defaults if LLM omitted them
    if "task_id" not in data or not data["task_id"]:
        data["task_id"] = str(uuid.uuid4())
    if "deadline_unix" not in data or not data["deadline_unix"]:
        data["deadline_unix"] = int(time.time()) + 3600
    if "budget" not in data:
        data["budget"] = 0.02

    task_spec = TaskSpec(**data)
    logger.info(f"requester_node: created TaskSpec id={task_spec.task_id} type={task_spec.task_type}")

    return {
        **state,
        "task_spec": task_spec,
        "candidate_executors": [],
        "audit_history": [],
        "retry_count": 0,
        "max_retries": MAX_RETRIES,
        "escrow_tx_hash": None,
        "reclaim_tx_hash": None,
        "reputation_tx_hash": None,
        "final_status": None,
        "escalation_reason": None,
    }
