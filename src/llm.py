"""LLM integration — Anthropic Claude API for pilot."""

import os
from pathlib import Path

import anthropic

from src.config import WORKSPACE_DIR

_client: anthropic.AsyncAnthropic | None = None
_system_prompt: str | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _load_file(path: Path) -> str:
    """Load a file if it exists, return empty string otherwise."""
    if path.exists():
        return path.read_text().strip()
    return ""


def _get_system_prompt() -> str:
    """Build system prompt from SOUL.md + MEMORY.md."""
    global _system_prompt
    if _system_prompt is None:
        soul = _load_file(WORKSPACE_DIR / "SOUL.md")
        memory = _load_file(WORKSPACE_DIR / "MEMORY.md")

        parts = []
        if soul:
            parts.append(soul)
        else:
            parts.append("You are Status App Agent, a helpful assistant in a Status Community chat.")
        if memory:
            parts.append(f"\n\n---\n\n# Long-term Memory\n\n{memory}")

        _system_prompt = "\n".join(parts)
    return _system_prompt


async def get_response(user_message: str, chat_id: str = "", context: str = "") -> str:
    """Get an LLM response to a user message."""
    client = _get_client()

    messages = []
    if context:
        messages.append({"role": "user", "content": f"Chat context:\n{context}"})
        messages.append({"role": "assistant", "content": "I've read the context. What's your question?"})

    messages.append({"role": "user", "content": user_message})

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=_get_system_prompt(),
        messages=messages,
    )

    return response.content[0].text
