# Architecture — v0 Pilot

## Overview

```
Status Community ←→ status-backend (Go, HTTP/WS) ←→ Python bot ←→ Anthropic API
```

The bot is a Python process that talks to `status-backend` (a Go HTTP server wrapping the full status-go library). status-backend handles all Status protocol complexity: Waku transport, E2E encryption, community membership, message formatting.

## Components

### 1. status-backend (Go)

Pre-built binary from [status-im/status-go](https://github.com/status-im/status-go/tree/develop/cmd/status-backend).

- Runs as a local HTTP server (default: `127.0.0.1:12345`)
- Exposes full status-go API via JSON-RPC (`POST /statusgo/CallRPC`)
- WebSocket signals at `ws://<host>/signals` for real-time events
- Manages its own database (messages, contacts, communities)

Key RPC methods (all require `"id"` field in JSON-RPC):
- `wakuext_startMessenger` — start Waku messaging (blocks 1s–10min on first run)
- `wakuext_joinedCommunities` — list joined communities
- `wakuext_createCommunity` — create new community
- `wakuext_requestToJoinCommunity` — request to join existing
- `wakuext_sendChatMessage({chatId, text, contentType: 1})` — send message
- `wakuext_chatMessages(chatID, cursor, limit)` — read history
- `settings_getSettings` — get account settings (display-name, public-key, key-uid)
- `sharedurls_shareCommunityURLWithData(communityID)` — get shareable link

Account lifecycle:
- `POST /statusgo/CreateAccountAndLogin` — create new account (generates BIP39 mnemonic)
- `POST /statusgo/LoginAccount` — login to existing account
- Wait for `node.login` WebSocket signal before making RPC calls

### 2. Python Bot

Our code. Connects to status-backend via HTTP + WebSocket.

Responsibilities:
- Listen for `messages.new` signals (WebSocket)
- Log all messages (JSONL chat logs)
- Call Anthropic API with SOUL.md + MEMORY.md as context
- Send response back via status-backend

### 3. Anthropic API (Cloud LLM)

Claude Sonnet for generating responses. System prompt = `SOUL.md` + `MEMORY.md`.

### 4. Workspace & Memory

All bot runtime data lives in `workspace/` (gitignored), separated from source code.

```
workspace/
├── SOUL.md      →  identity + behavior rules (always in system prompt)
├── MEMORY.md    →  long-term facts (always in system prompt)
├── memory/      →  daily logs + topic files (future RAG retrieval)
├── logs/        →  raw chat JSONL (analytics, never sent to LLM)
└── data/        →  status-backend DB, keystore, wallet
```

## Data Flow

```
1. User sends message in Status Community
2. Waku delivers message to status-backend
3. status-backend emits `messages.new` WebSocket signal
4. Python bot receives signal, logs to JSONL
5. Bot builds context: SOUL.md + MEMORY.md + user message
6. Bot sends to Anthropic API
7. Claude returns response
8. Bot sends response via status-backend RPC, logs to JSONL
9. status-backend sends via Waku to community
10. User sees bot's reply in chat
```

## Authentication

Bot account = ECDSA secp256k1 keypair from BIP39 mnemonic (12 words).
- Chat identity key derived at `m/43'/60'/1581'/0'/0` (EIP1581)
- Bot appears as regular Status account
- Store `key_uid` in `.env` file (gitignored) for re-login

## File Structure

```
status-app-agent/
├── AGENTS.md              # Project instructions for AI/devs
├── CLAUDE.md              # Claude Code adapter
├── workspace/             # All bot runtime data (gitignored)
│   ├── SOUL.md            # Bot identity → system prompt
│   ├── MEMORY.md          # Long-term canon → system prompt
│   ├── memory/
│   │   ├── YYYY-MM-DD.md  # Daily decisions/events
│   │   └── topics/        # Domain knowledge files
│   ├── logs/
│   │   └── chat-YYYY-MM-DD.jsonl  # Raw chat messages
│   └── data/              # status-backend DB, keystore
├── src/
│   ├── bot.py             # Main bot (WS listener + message handler)
│   ├── status_client.py   # Async HTTP/WS wrapper for status-backend
│   ├── llm.py             # Anthropic API + prompt assembly
│   ├── chat_log.py        # JSONL chat logger
│   └── config.py          # Settings (env vars, WORKSPACE_DIR)
├── scripts/
│   ├── setup_status_backend.sh
│   └── test_connection.py
├── bin/                   # Pre-built binaries (gitignored)
├── vendor/                # status-go source (gitignored)
├── docs/
│   ├── architecture.md    # This file
│   └── proposal.pdf       # Original proposal
├── .env.example
└── pyproject.toml
```

## Risks & Open Questions

- **status-backend stability** — no official docs, no API stability guarantees
- **Community discovery** — bot-created communities may not be visible to desktop clients (Waku peer overlap)
- **Rate limiting** — unclear if Status/Waku has rate limits on messages
- **Memory growth** — MEMORY.md injected on every call; must stay concise to avoid token bloat
- **Conversation context from logs** — bot loads last 20 messages from JSONL chat log for the same chat_id. Not persistent across bot restarts if logs are cleared
- **Cross-channel information leakage** — conversation context is isolated per chat_id (safe in Phase 0). But future RAG (Phase 2) with a shared vector store could leak private channel content into public channel answers. RAG index must be per-channel or enforce access control. Same applies to auto-extracted MEMORY.md facts — must track source channel
