"""
executor_code.py — Code Executor sub-node.
LLM generates a Python function based on task_spec.description.
Output goes into executor_output as a string containing the raw code.
Must NOT execute anything itself — execution happens only inside code_sandbox.py,
called by the Auditor.
"""
import logging

from backend.state import AgentState, AuditVerdict
from backend.tools.llm_client import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Python coding agent. Your job is to implement a Python function exactly as described.

RULES:
- Output ONLY the raw Python code. No markdown fences, no explanations, no extra text.
- The function must be importable from a module named 'solution'.
- Handle edge cases explicitly.
- Do NOT use external libraries — only Python standard library.
- Do NOT add any if __name__ == '__main__' block.
"""


def executor_code_node(state: AgentState) -> AgentState:
    """
    Generates Python code for the task via LLM.
    Injects the latest audit critique if this is a retry (Reflexion loop).
    """
    task_spec = state["task_spec"]
    audit_history = state["audit_history"]
    retry_count = state["retry_count"]

    # Build user message — inject critique on retry (Reflexion)
    user_content = f"Task: {task_spec.description}\n\nAcceptance criteria:\n"
    for criterion in task_spec.acceptance_criteria:
        user_content += f"- {criterion}\n"

    if retry_count > 0 and audit_history:
        latest_critique = audit_history[-1].critique
        user_content += f"\n\nPREVIOUS ATTEMPT FAILED. Auditor critique:\n{latest_critique}\n\nPlease fix the code based on this critique."
        logger.info(f"executor_code_node: retry #{retry_count}, injecting critique")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    logger.info(f"executor_code_node: generating code for task_id={task_spec.task_id}")
    code = call_llm(messages, temperature=0.2, max_tokens=2048)

    # Strip markdown fences if present
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first and last lines (the fences)
        code = "\n".join(lines[1:-1]).strip()

    logger.info(f"executor_code_node: generated {len(code)} chars of code")
    return {
        **state,
        "executor_output": code,
    }
