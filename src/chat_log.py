"""Chat log — append-only JSONL daily logs + recent history retrieval."""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.config import WORKSPACE_DIR

LOGS_DIR = WORKSPACE_DIR / "logs"

# Max messages to include as conversation context
CONTEXT_WINDOW = 20


def log_message(
    direction: str,  # "in" or "out"
    text: str,
    chat_id: str = "",
    from_key: str = "",
    message_id: str = "",
):
    """Append a chat message to today's JSONL log."""
    LOGS_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    log_file = LOGS_DIR / f"chat-{now.strftime('%Y-%m-%d')}.jsonl"

    entry = {
        "ts": now.isoformat(),
        "dir": direction,
        "chat_id": chat_id,
        "from": from_key[:40] if from_key else "",
        "text": text,
    }
    if message_id:
        entry["msg_id"] = message_id

    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_recent_context(chat_id: str, limit: int = CONTEXT_WINDOW) -> str:
    """Load recent messages from the same chat as conversation context.

    Returns formatted string for LLM context injection.
    Scans today's log file (and yesterday's if needed).
    """
    if not LOGS_DIR.exists():
        return ""

    # Collect log files (today + yesterday)
    log_files = sorted(LOGS_DIR.glob("chat-*.jsonl"))[-2:]

    messages = []
    for log_file in log_files:
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("chat_id") == chat_id:
                        messages.append(entry)
                except json.JSONDecodeError:
                    continue

    if not messages:
        return ""

    # Take last N messages
    recent = messages[-limit:]

    # Format as conversation
    lines = []
    for msg in recent:
        role = "Bot" if msg["dir"] == "out" else "User"
        lines.append(f"{role}: {msg['text']}")

    return "\n".join(lines)
