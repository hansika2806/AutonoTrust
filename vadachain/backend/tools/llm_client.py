"""
llm_client.py — Groq primary LLM + OpenRouter fallback.
Implement Groq call first, catch rate-limit/error, fall back to OpenRouter.
"""
import logging
from typing import Optional
from groq import Groq
from openai import OpenAI

from backend.config import (
    GROQ_API_KEY, GROQ_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL,
)

logger = logging.getLogger(__name__)


def call_llm(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 2048,
    response_format: Optional[dict] = None,
) -> str:
    """
    Call Groq LLM first. If it fails (rate limit or error), fall back to OpenRouter.
    Returns the raw string content of the assistant message.
    """
    # --- Primary: Groq ---
    try:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        client = Groq(api_key=GROQ_API_KEY)
        kwargs: dict = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"Groq call failed ({e}), falling back to OpenRouter...")

    # --- Fallback: OpenRouter ---
    try:
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")
        client_or = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
        kwargs_or: dict = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp_or = client_or.chat.completions.create(**kwargs_or)
        return resp_or.choices[0].message.content or ""
    except Exception as e2:
        logger.error(f"OpenRouter fallback also failed: {e2}")
        raise RuntimeError(
            f"Both Groq and OpenRouter LLM calls failed. Last error: {e2}"
        ) from e2
