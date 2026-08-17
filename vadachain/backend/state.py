"""
state.py — AgentState, TaskSpec, ExecutorProfile, AuditVerdict.
Implement exactly as specified in the build spec.
"""
from typing import TypedDict, Literal, Optional
from pydantic import BaseModel


class TaskSpec(BaseModel):
    task_id: str
    description: str
    acceptance_criteria: list[str]
    budget: float
    task_type: Literal["code", "research", "writing"]
    deadline_unix: int


class ExecutorProfile(BaseModel):
    agent_id: str
    wallet_address: str
    skills: list[str]
    past_success_rate: float
    tasks_completed: int


class AuditVerdict(BaseModel):
    passed: bool
    confidence: float
    critique: str
    retrieved_precedents: list[str]  # empty list until Phase 4 (RAG)


class AgentState(TypedDict):
    raw_request: str
    task_spec: Optional[TaskSpec]
    candidate_executors: list[ExecutorProfile]
    chosen_executor: Optional[str]
    executor_output: Optional[str]
    audit_history: list[AuditVerdict]
    retry_count: int
    max_retries: int
    escrow_tx_hash: Optional[str]
    reclaim_tx_hash: Optional[str]
    reputation_tx_hash: Optional[str]
    final_status: Optional[Literal["paid", "refunded", "escalated"]]
    escalation_reason: Optional[str]
