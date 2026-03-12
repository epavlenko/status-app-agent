# AGENTS.md — Status app Agent

Privacy-preserving AI agents for Status Communities. Local LLM inference, Waku transport, zero-leak architecture — no user data leaves the community's control.

**Stack:** Python 3.12+, uv, Status SDK/status-go, Anthropic API (pilot), SQLite, ChromaDB (vector store).

## Development Setup

```bash
uv sync                                         # install Python deps
./scripts/setup_status_backend.sh               # start status-backend on port 12345
uv run python scripts/test_connection.py        # test: create account, connect to Waku
uv run python -m src.bot                        # run the bot
uv run pytest                                   # tests
```

**Always use `uv`, never `pip` directly.**
Pre-built `status-backend` binary + `libsds.dylib` in `bin/`. To rebuild from source: see `vendor/status-go/`.

## Architecture (v0 Pilot)

```
Status Community ←→ status-backend (Go, HTTP/WS) ←→ Python bot ←→ Anthropic API
```

Bot connects to `status-backend` (HTTP server wrapping status-go) which handles all Status protocol: Waku, E2E encryption, community membership, message formatting.

See [`docs/architecture.md`](docs/architecture.md) for details.

### Layers

| Layer | Purpose | Location |
|-------|---------|----------|
| Transport | status-backend HTTP/WS client | `src/status_client.py` |
| Inference | Anthropic API (pilot) / Ollama (v1) | `src/llm.py` |
| Bot logic | Message handling, signal dispatch | `src/bot.py` |
| Chat log | Append-only JSONL daily logs | `src/chat_log.py` → `logs/` |
| Config | Environment variables | `src/config.py` |

### Workspace

All bot runtime data lives in `workspace/` — separated from source code. Gitignored.

```
workspace/
├── SOUL.md          →  system prompt (identity, behavior rules)
├── MEMORY.md        →  long-term canon (injected into every LLM call)
├── memory/          →  daily logs + topic files (for future RAG retrieval)
├── logs/            →  raw chat JSONL (for analytics and context)
└── data/            →  status-backend DB, keystore, wallet
```

| File | Purpose | Loaded |
|------|---------|--------|
| `workspace/SOUL.md` | Bot identity and behavior | Always (system prompt) |
| `workspace/MEMORY.md` | Core decisions, known members, community rules | Always (appended to system prompt) |
| `workspace/memory/YYYY-MM-DD.md` | Daily decisions, corrections, follow-ups | On demand (future) |
| `workspace/memory/topics/*.md` | Deep domain knowledge (API caveats, patterns) | On demand (future RAG) |
| `workspace/logs/chat-YYYY-MM-DD.jsonl` | Raw in/out messages | Never loaded to LLM (analytics only) |
| `workspace/data/` | status-backend SQLite DBs, keystore | Never (infra only) |

### Three Agent Concepts

All share the same transport/inference/storage layers. Pilot one first, extend later.

1. **Knowledge Agent** — builds community knowledge base from discussions, answers recurring questions via RAG
2. **Coordinator Agent** — tracks decisions, action items, deadlines; generates summaries
3. **Onboarding Guide** — greets new members, walks through community rules, connects to relevant people

## Key Decisions

- **Python over Go/Nim** — Logos ecosystem uses Nim (Waku, Codex, Status client) and Go (status-go, go-waku), but Python has vastly superior LLM/RAG tooling (Ollama, ChromaDB, langchain, sentence-transformers). For a 3-week pilot, Python enables fast iteration. Production rewrite to Go is an option after validating the concept
- **uv over pip** — fast, reproducible dependency management
- **Ollama for inference** — simple API, supports all target models, easy self-hosting
- **ChromaDB for vectors** — embedded, no infra needed, Python-native
- **SQLite for structured data** — zero infrastructure, WAL mode, sufficient for community-scale

## Gotchas

- **status-backend build** requires Go + protoc + Nim (for libsds). Pre-built binary in `bin/`
- **`startMessenger` takes ~10 min** on first launch (Waku peer discovery, mailserver sync). Must be called async
- **WebSocket ping** — status-backend doesn't respond to WS pings. Use `ping_interval=None` in websockets client
- **RPC blocks during startMessenger** — all `CallRPC` calls queue behind it. Use separate HTTP connection or wait for completion
- **Startup sequence**: WebSocket connect → InitializeApplication → CreateAccountAndLogin → wait for `node.login` signal → CallRPC `wakuext_startMessenger` → wait for completion → then other RPC calls work
- **Signals to watch**: `node.login` (auth done), `mailserver.available` (can sync history), `history.request.completed` (history synced)
- **JSON-RPC `id` is required** — omitting it causes empty/error responses from status-backend
- **LoginAccount returns "already running"** if backend wasn't restarted — handle gracefully, skip login wait
- **Don't call LoginAccount on running node** — causes node.crashed → node.stopped → restart, losing community state. Check `settings_getSettings` first; if it returns a public-key, skip login
- **Waku P2P between two nodes on same machine** — community membership operations (invite, requestToJoin approval) may not be delivered. Contact requests work. Workaround: run bot on a separate host
- **Account = ECDSA keypair** from BIP39 mnemonic. Store key_uid in `.env` for re-login

## Execution Scope

See [`docs/roadmap.md`](docs/roadmap.md) for the full phased roadmap.

- **Phase 0 (done):** Bot in Status Community — cloud LLM, SOUL.md identity, @mention filter, conversation context, chat history loading, chat logging, auto-accept contacts & community invites
- **Phase 1 (next):** Token-based context, summarization, multi-user awareness
- **Phase 2:** RAG knowledge base from community discussions
- **Phase 3:** Local inference (Ollama), privacy-preserving
- **Phase 4:** Multi-agent (Knowledge + Coordinator + Onboarding)
- **Phase 5:** Immutable Notes integration — shared encrypted knowledge vault
- **Phase 6:** Full Logos Stack — Nomos, native Waku, payments

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/proposal.pdf`](docs/proposal.pdf) | Original proposal document (full vision) |
| [`docs/architecture.md`](docs/architecture.md) | Architecture, memory system, file structure |
| [`docs/roadmap.md`](docs/roadmap.md) | Phased roadmap (Phase 0–6) |

## Maintaining AGENTS.md and CLAUDE.md

| File | Audience | Content |
|------|----------|---------|
| `AGENTS.md` (this file) | Any AI agent | Project instructions: architecture, build, patterns, gotchas |
| `CLAUDE.md` | Claude Code only | `Read AGENTS.md` + knowledge base link + hooks, skills |

**Rules:**
- "Remember this" → save to `AGENTS.md` so all agents benefit
- Project knowledge (architecture, patterns, gotchas) → `AGENTS.md`
- Claude Code settings (hooks, skills, vault) → `CLAUDE.md`
- Don't duplicate project instructions in `CLAUDE.md`
- Keep both files concise; move details to `docs/`
- **After any code change** — update related docs (README, AGENTS.md, `docs/`) in the same commit. Code without updated docs is incomplete
