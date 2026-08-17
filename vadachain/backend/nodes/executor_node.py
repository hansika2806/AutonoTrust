"""
executor_node.py — Router node: dispatches to code/research/writing sub-nodes.
Phase 1: only code tasks are supported.
"""
import logging

from backend.state import AgentState
from backend.nodes.executor_code import executor_code_node

logger = logging.getLogger(__name__)


def executor_node(state: AgentState) -> AgentState:
    """
    Dispatches to the appropriate executor sub-node based on task_type.
    Phase 1: only 'code' is handled; other types raise NotImplementedError.
    Phase 5 will add executor_research and executor_writing.
    """
    task_type = state["task_spec"].task_type
    logger.info(f"executor_node: routing task_type={task_type}")

    if task_type == "code":
        return executor_code_node(state)
    elif task_type in ("research", "writing"):
        # Phase 5: import and call executor_research_node / executor_writing_node
        raise NotImplementedError(
            f"Task type '{task_type}' is only available in Phase 5. "
            "Currently only 'code' tasks are supported."
        )
    else:
        raise ValueError(f"Unknown task_type: {task_type}")
