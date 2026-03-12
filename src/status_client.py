"""Async client for status-backend HTTP/WebSocket API."""

import asyncio
import json
import logging

import httpx
import websockets

logger = logging.getLogger(__name__)


class StatusClient:
    """Async wrapper around status-backend HTTP + WebSocket API."""

    def __init__(self, base_url: str = "http://127.0.0.1:12345"):
        self.base_url = base_url.rstrip("/")
        self.ws_url = self.base_url.replace("http", "ws") + "/signals"
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)
        self._rpc_id = 0

    # --- HTTP API ---

    async def health(self) -> dict:
        r = await self._http.get("/health")
        return r.json()

    async def initialize(self, data_dir: str) -> dict:
        r = await self._http.post("/statusgo/InitializeApplication", json={"dataDir": data_dir})
        return r.json()

    async def create_account(self, display_name: str, password: str, data_dir: str) -> dict:
        r = await self._http.post("/statusgo/CreateAccountAndLogin", json={
            "rootDataDir": data_dir,
            "displayName": display_name,
            "password": password,
            "customizationColor": "primary",
        })
        return r.json()

    async def login(self, key_uid: str, password: str) -> dict:
        r = await self._http.post("/statusgo/LoginAccount", json={
            "keyUID": key_uid,
            "password": password,
        })
        return r.json()

    async def call_rpc(self, method: str, params: list | None = None) -> dict:
        """Call a JSON-RPC method via status-backend."""
        self._rpc_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._rpc_id,
            "method": method,
            "params": params or [],
        }
        r = await self._http.post("/statusgo/CallRPC", json=payload)
        return r.json()

    async def start_messenger(self) -> dict:
        return await self.call_rpc("wakuext_startMessenger")

    async def joined_communities(self) -> list:
        result = await self.call_rpc("wakuext_joinedCommunities")
        return result.get("result") or []

    async def join_community(self, community_id: str) -> dict:
        return await self.call_rpc("wakuext_requestToJoinCommunity", [{"communityId": community_id}])

    async def send_chat_message(self, chat_id: str, text: str) -> dict:
        return await self.call_rpc("wakuext_sendChatMessage", [{
            "chatId": chat_id,
            "text": text,
            "contentType": 1,  # text message
        }])

    async def chat_messages(self, chat_id: str, cursor: str = "", limit: int = 20) -> dict:
        return await self.call_rpc("wakuext_chatMessages", [chat_id, cursor, limit])

    async def get_settings(self) -> dict:
        result = await self.call_rpc("settings_getSettings")
        return result.get("result") or {}

    async def accept_contact_request(self, contact_id: str) -> dict:
        """Accept the latest contact request from a given contact."""
        return await self.call_rpc("wakuext_acceptLatestContactRequestForContact", [{"id": contact_id}])

    async def accept_all_pending_contact_requests(self) -> int:
        """Find contacts who added us but we haven't added back, and accept them.
        Returns number of accepted requests."""
        result = await self.call_rpc("wakuext_contacts")
        contacts = result.get("result") or []
        accepted = 0
        for c in contacts:
            if c.get("hasAddedUs") and not c.get("added"):
                contact_id = c["id"]
                logger.info("Accepting contact request from %s (%s...)", c.get("displayName", "?"), contact_id[:20])
                await self.accept_contact_request(contact_id)
                accepted += 1
        return accepted

    async def accept_community_invitations(self) -> int:
        """Check activity center for community invitations and accept them.
        Returns number of accepted invitations."""
        # Type 6 = community invitation
        result = await self.call_rpc("wakuext_activityCenterNotifications", [
            {"activityTypes": [6], "cursor": "", "limit": 50, "readType": 1}
        ])
        notifications = ((result.get("result") or {}).get("activityCenterNotifications") or {}).get("notifications") or []
        accepted = 0
        for n in notifications:
            community_id = n.get("communityId", "")
            notif_id = n.get("id", "")
            if community_id:
                logger.info("Accepting community invitation: %s (notif %s...)", community_id[:20], notif_id[:20])
                await self.call_rpc("wakuext_acceptActivityCenterNotifications", [{"ids": [notif_id]}])
                accepted += 1
        if not notifications:
            # Also check if there are communities we can see but haven't joined
            # (e.g., if owner added us directly)
            result = await self.call_rpc("wakuext_communities")
            communities = result.get("result") or []
            for c in communities:
                if not c.get("joined") and c.get("isMember"):
                    cid = c.get("id", "")
                    logger.info("Found unjoinable community, joining: %s", c.get("name"))
                    # Get wallet address for join
                    accts = await self.call_rpc("accounts_getAccounts")
                    wallet_addr = ""
                    for a in (accts.get("result") or []):
                        if a.get("wallet"):
                            wallet_addr = a["address"]
                            break
                    if wallet_addr:
                        await self.call_rpc("wakuext_requestToJoinCommunity", [{
                            "communityId": cid,
                            "addressesToReveal": [wallet_addr],
                            "airdropAddress": wallet_addr,
                        }])
                        accepted += 1
        return accepted

    # --- WebSocket Signals ---

    async def listen_signals(self, handler):
        """Connect to WebSocket and dispatch signals to handler.

        handler is an async callable: async def handler(signal_type: str, event: dict)
        """
        logger.info("Connecting to signals WebSocket: %s", self.ws_url)
        async for ws in websockets.connect(self.ws_url, ping_interval=None):
            try:
                async for message in ws:
                    try:
                        signal = json.loads(message)
                        signal_type = signal.get("type", "")
                        event = signal.get("event", {})
                        if signal_type not in ("wakuv2.peerstats",):
                            logger.info("Signal: %s", signal_type)
                        await handler(signal_type, event)
                    except json.JSONDecodeError:
                        logger.warning("Non-JSON signal: %s", message[:200])
            except websockets.ConnectionClosed:
                logger.warning("WebSocket closed, reconnecting...")
                continue

    async def close(self):
        await self._http.aclose()
