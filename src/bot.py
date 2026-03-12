"""Main bot: connects to Status Community, responds to messages via LLM."""

import asyncio
import logging
import os

from dotenv import load_dotenv

from .config import STATUS_DATA_DIR
from .status_client import StatusClient
from .llm import get_response
from .chat_log import log_message, get_recent_context

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class StatusBot:
    def __init__(self):
        self.base_url = os.getenv("STATUS_BACKEND_URL", "http://127.0.0.1:12345")
        self.data_dir = STATUS_DATA_DIR
        self.client = StatusClient(self.base_url)
        self.bot_name = os.getenv("STATUS_BOT_NAME", "Status App Agent")
        self.key_uid = os.getenv("STATUS_BOT_KEY_UID", "")
        self.password = os.getenv("STATUS_BOT_PASSWORD", "status-agent-bot")
        self.community_id = os.getenv("STATUS_COMMUNITY_ID", "")
        self._ready = asyncio.Event()
        self._messenger_ready = asyncio.Event()
        self._my_public_key = ""

    async def start(self):
        """Initialize and start the bot."""
        # 1. Health check
        health = await self.client.health()
        logger.info("status-backend alive: %s", health)

        # 2. Initialize
        result = await self.client.initialize(self.data_dir)
        accounts = result.get("accounts") or []
        logger.info("Initialized, existing accounts: %d", len(accounts))

        # 3. Start signal listener in background
        signal_task = asyncio.create_task(self.client.listen_signals(self._handle_signal))

        # 4. Check if node is already running (avoid crashing it with duplicate login)
        already_running = False
        try:
            settings = await self.client.get_settings()
            if settings.get("public-key"):
                logger.info("Node already running and logged in, skipping login")
                already_running = True
                self._ready.set()
        except Exception:
            pass

        if not already_running:
            # Login or create account
            if self.key_uid:
                logger.info("Logging in with key_uid: %s...", self.key_uid[:20])
                result = await self.client.login(self.key_uid, self.password)
            elif accounts:
                acct = accounts[0]
                self.key_uid = acct["key-uid"]
                logger.info("Logging in as '%s'...", acct.get("name", "?"))
                result = await self.client.login(self.key_uid, self.password)
            else:
                logger.info("Creating new account: %s", self.bot_name)
                result = await self.client.create_account(self.bot_name, self.password, self.data_dir)

            error = result.get("error", "")
            if error and "already running" not in error:
                logger.error("Account error: %s", error)
                return
            if "already running" in error:
                logger.info("Node already running, skipping login wait")
                self._ready.set()

        # 5. Wait for node.login signal
        if not self._ready.is_set():
            logger.info("Waiting for login signal...")
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=30)
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for node.login, proceeding anyway")

        # 6. Start messenger
        if not already_running:
            logger.info("Starting messenger (this may take a while)...")
            result = await self.client.start_messenger()
            error = result.get("error", {})
            if isinstance(error, dict):
                error = error.get("message", "")
            if error and "crashed" not in str(error):
                logger.error("Messenger error: %s", error)
                return
            if error:
                logger.warning("Messenger may already be running (%s), proceeding", error)
            else:
                logger.info("Messenger started!")
        else:
            logger.info("Messenger already running")
        self._messenger_ready.set()

        # 7. Get bot's own public key
        settings = await self.client.get_settings()
        self._my_public_key = settings.get("public-key", "")
        logger.info("Bot public key: %s...", self._my_public_key[:40] if self._my_public_key else "unknown")

        # 8. Accept any pending contact requests and community invitations
        accepted = await self.client.accept_all_pending_contact_requests()
        if accepted:
            logger.info("Accepted %d pending contact request(s)", accepted)
        invited = await self.client.accept_community_invitations()
        if invited:
            logger.info("Accepted %d community invitation(s)", invited)

        # 9. List communities and load chat history
        communities = await self.client.joined_communities()
        if communities:
            for c in communities:
                cid = c.get("id", "")
                logger.info("Community: %s (%s)", c.get("name"), cid[:20])
                # Load recent history for each channel
                for chat_key in (c.get("chats") or {}):
                    full_chat_id = cid + chat_key
                    await self._load_chat_history(full_chat_id)
        else:
            logger.info("No communities joined yet")

        logger.info("Bot is running. Listening for messages...")
        await signal_task

    async def _load_chat_history(self, chat_id: str):
        """Load recent messages from status-backend into chat log."""
        try:
            result = await self.client.chat_messages(chat_id, limit=50)
            messages = (result.get("result") or {}).get("messages") or []
            if not messages:
                return
            # Sort by timestamp (oldest first) and log them
            messages.sort(key=lambda m: m.get("whisperTimestamp", 0))
            for msg in messages:
                text = msg.get("text", "")
                if not text or msg.get("contentType", 0) != 1:
                    continue
                from_key = msg.get("from", "")
                direction = "out" if from_key == self._my_public_key else "in"
                log_message(direction, text, chat_id=chat_id, from_key=from_key, message_id=msg.get("id", ""))
            logger.info("Loaded %d messages from %s...", len(messages), chat_id[:30])
        except Exception as e:
            logger.warning("Failed to load history for %s: %s", chat_id[:30], e)

    async def _handle_signal(self, signal_type: str, event: dict):
        """Handle incoming WebSocket signals."""
        if signal_type == "node.login":
            error = event.get("error", "")
            if error and "already running" in error:
                logger.info("Node already running (signal), proceeding")
                self._ready.set()
            elif error:
                logger.error("Login failed: %s", error)
            else:
                logger.info("Login successful!")
                self._ready.set()

        elif signal_type == "messages.new":
            if not self._messenger_ready.is_set():
                return  # ignore messages before messenger is ready
            messages = event.get("messages", [])
            for msg in messages:
                await self._handle_message(msg)

        elif signal_type in ("activity-center-notifications", "contact.update", "community.found"):
            # Auto-accept incoming contact requests and community invitations
            if self._messenger_ready.is_set():
                try:
                    accepted = await self.client.accept_all_pending_contact_requests()
                    if accepted:
                        logger.info("Auto-accepted %d contact request(s)", accepted)
                    invited = await self.client.accept_community_invitations()
                    if invited:
                        logger.info("Auto-accepted %d community invitation(s)", invited)
                except Exception as e:
                    logger.warning("Failed to auto-accept: %s", e)

    def _should_respond(self, msg: dict) -> bool:
        """Decide whether to respond to a message.

        Responds if:
        - Bot is explicitly mentioned (status-go sets "mentioned": true)
        - Bot name appears in text (fallback for text-based mentions)
        - Message is a 1-on-1 DM (chatType 1)
        """
        # status-go computed mention flag
        if msg.get("mentioned"):
            return True

        # Text-based mention fallback
        text = msg.get("text", "").lower()
        if self.bot_name.lower() in text:
            return True

        # 1-on-1 chat (not community)
        if msg.get("chatType") == 1:
            return True

        return False

    async def _handle_message(self, msg: dict):
        """Process an incoming chat message."""
        text = msg.get("text", "")
        from_key = msg.get("from", "")
        chat_id = msg.get("chatId", "")
        content_type = msg.get("contentType", 0)

        # Only handle text messages
        if content_type != 1:
            return

        # Skip own messages
        if from_key == self._my_public_key:
            return

        if not text.strip():
            return

        # Always log incoming messages (for context)
        log_message("in", text, chat_id=chat_id, from_key=from_key, message_id=msg.get("id", ""))

        # Only respond if mentioned or DM
        if not self._should_respond(msg):
            logger.debug("Skipping (not mentioned): %s", text[:60])
            return

        logger.info("Message from %s...: %s", from_key[:20], text[:100])

        try:
            context = get_recent_context(chat_id)
            response = await get_response(text, chat_id=chat_id, context=context)
            await self.client.send_chat_message(chat_id, response)
            logger.info("Replied in %s: %s", chat_id[:30], response[:100])
            log_message("out", response, chat_id=chat_id, from_key=self._my_public_key)
        except Exception as e:
            logger.error("Failed to respond: %s", e)


async def main():
    bot = StatusBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
