# Status App Agent v0.1.0

Privacy-preserving AI agents for [Status](https://status.app/) Communities. Local LLM inference, Logos Messaging transport, zero-leak architecture — no user data leaves the community's control.

> **v0.1.0** is a proof-of-concept that uses a cloud LLM (Anthropic API). Local inference is planned for v0.4.0.

## Problem

Status Communities lack tools for knowledge management, onboarding, and coordination. Members ask the same questions repeatedly, decisions get lost in chat history, and new members have no guide.

## Why Not Existing Solutions?

| Approach | Problem |
|----------|---------|
| Discord/Telegram bots | All messages routed through a third party. One subpoena and the community's private discussions are exposed |
| "Just use ChatGPT" | Context is lost. No memory, no automation, no integration with the chat flow |
| Self-hosted AI | Requires DevOps + GPU. Messages must leave E2E encrypted channel to reach the server |
| **Our approach** | **Agent lives *inside* the Status protocol — Logos Messaging transport, community-owned inference, existing E2E encryption** |

## Demo

https://github.com/epavlenko/status-app-agent/raw/main/docs/demo.mp4

## Quick Start

```bash
uv sync                                # install dependencies
cp .env.example .env                   # configure (API keys, community ID)
./scripts/setup_status_backend.sh      # start status-backend
uv run python -m src.bot               # run the bot
```

## Architecture

```
Status Community <-> status-backend (Go, HTTP/WS) <-> Python bot <-> Anthropic API (temporary, to be changed to local inference)
```

See [docs/architecture.md](docs/architecture.md) for details.

## Roadmap

| Version | Phase | Description |
|---------|-------|-------------|
| **v0.1.0** | Phase 0 | Bot in Status Community, cloud LLM, chat context ✅ |
| v0.2.0 | Phase 1 | Token-based context, summarization, multi-user awareness |
| v0.3.0 | Phase 2 | RAG knowledge base from community discussions |
| v0.4.0 | Phase 3 | Local inference (Ollama), zero-leak architecture |
| v0.5.0 | Phase 4 | Multi-agent (Knowledge + Coordinator + Onboarding) |
| v0.6.0 | Phase 5 | Immutable Notes integration |
| v1.0.0 | Phase 6 | Full Logos Stack (Nomos, native Logos Messaging, payments) |

See [docs/roadmap.md](docs/roadmap.md) for the full vision and phased plan.

## License

MIT
