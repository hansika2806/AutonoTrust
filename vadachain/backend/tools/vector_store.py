"""
vector_store.py — Chroma persistent client wrapper with two collections:
  - task_precedents: past task descriptions + final audit verdicts + critiques
  - source_documents: for Phase 5 research/writing tasks only

Phase 1-3: stub (returns empty results).
Phase 4: full Chroma implementation activated.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_CHROMA_AVAILABLE = False
_client = None
_task_precedents_collection = None
_source_documents_collection = None


def _init_chroma():
    """Lazily initialize Chroma client."""
    global _CHROMA_AVAILABLE, _client, _task_precedents_collection, _source_documents_collection
    if _CHROMA_AVAILABLE:
        return
    try:
        import chromadb
        from backend.config import CHROMA_PERSIST_DIR
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _task_precedents_collection = _client.get_or_create_collection(
            name="task_precedents",
            metadata={"description": "Past task descriptions, verdicts, and critiques"},
        )
        _source_documents_collection = _client.get_or_create_collection(
            name="source_documents",
            metadata={"description": "Source documents for Phase 5 research tasks"},
        )
        _CHROMA_AVAILABLE = True
        logger.info("vector_store: Chroma initialized successfully")
    except Exception as e:
        logger.warning(f"vector_store: Chroma unavailable ({e}), using stub mode")


def add_task_precedent(
    task_id: str,
    description: str,
    verdict_passed: bool,
    critique: str,
) -> None:
    """
    Write task description + final verdict + critique into task_precedents collection.
    Called after every completed task (in reporter_node or memory_write_node in Phase 4).
    """
    _init_chroma()
    if not _CHROMA_AVAILABLE:
        logger.debug("vector_store: stub mode, skipping add_task_precedent")
        return
    document = f"Task: {description}\nPassed: {verdict_passed}\nCritique: {critique}"
    _task_precedents_collection.upsert(
        ids=[task_id],
        documents=[document],
        metadatas=[{
            "task_id": task_id,
            "passed": str(verdict_passed),
            "critique": critique[:500],
        }],
    )
    logger.info(f"vector_store: stored precedent for task_id={task_id}")


def retrieve_task_precedents(query: str, top_k: int = 3) -> list[str]:
    """
    Retrieve top-k most similar task precedents for a given query description.
    Used by Matcher and Auditor in Phase 4.
    Returns list of precedent strings, or empty list if Chroma unavailable.
    """
    _init_chroma()
    if not _CHROMA_AVAILABLE:
        return []
    try:
        results = _task_precedents_collection.query(
            query_texts=[query],
            n_results=min(top_k, _task_precedents_collection.count()),
        )
        docs = results.get("documents", [[]])[0]
        logger.info(f"vector_store: retrieved {len(docs)} precedents for query")
        return docs
    except Exception as e:
        logger.warning(f"vector_store: precedent retrieval failed ({e})")
        return []


def add_source_document(doc_id: str, content: str, metadata: Optional[dict] = None) -> None:
    """Add a source document for Phase 5 research tasks."""
    _init_chroma()
    if not _CHROMA_AVAILABLE:
        return
    _source_documents_collection.upsert(
        ids=[doc_id],
        documents=[content],
        metadatas=[metadata or {}],
    )


def retrieve_source_documents(query: str, top_k: int = 3) -> list[str]:
    """Retrieve source documents for Phase 5 research tasks."""
    _init_chroma()
    if not _CHROMA_AVAILABLE:
        return []
    try:
        results = _source_documents_collection.query(
            query_texts=[query],
            n_results=min(top_k, _source_documents_collection.count()),
        )
        return results.get("documents", [[]])[0]
    except Exception as e:
        logger.warning(f"vector_store: source doc retrieval failed ({e})")
        return []
