# Status App Agent

Privacy-preserving AI agents for [Status](https://status.app/) Communities. Local LLM inference, Logos Messaging transport, zero-leak architecture — no user data leaves the community's control.

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

- **Phase 0** — Bot in Status Community, cloud LLM, chat context ✅
- **Phase 1** — Token-based context, summarization, multi-user awareness
- **Phase 2** — RAG knowledge base from community discussions
- **Phase 3** — Local inference (Ollama), zero-leak architecture
- **Phase 4** — Multi-agent (Knowledge + Coordinator + Onboarding)
- **Phase 5** — Immutable Notes integration
- **Phase 6** — Full Logos Stack (Nomos, native Logos Messaging, payments)

See [docs/roadmap.md](docs/roadmap.md) for the full vision and phased plan.

## License

MIT
