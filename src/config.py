"""Configuration from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", str(PROJECT_ROOT / "workspace"))).resolve()

STATUS_BACKEND_URL = os.getenv("STATUS_BACKEND_URL", "http://127.0.0.1:12345")
STATUS_DATA_DIR = str(Path(os.getenv("STATUS_DATA_DIR", str(WORKSPACE_DIR / "data"))).resolve())
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
STATUS_BOT_NAME = os.getenv("STATUS_BOT_NAME", "Status App Agent")
STATUS_BOT_KEY_UID = os.getenv("STATUS_BOT_KEY_UID", "")
STATUS_BOT_PASSWORD = os.getenv("STATUS_BOT_PASSWORD", "status-agent-bot")
