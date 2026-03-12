# Roadmap — Status App Agent

Privacy-preserving AI agents for Status Communities. Local LLM inference, Waku transport, zero-leak architecture — no user data leaves the community's control.

## Problem

Status Communities lack tools for knowledge management, onboarding, and coordination. Members ask the same questions repeatedly, decisions get lost in chat history, and new members have no guide. Traditional bots require centralized servers that leak metadata and break the trust model of a privacy-first messenger.

## Previous Attempts & Hypotheses

**Wave 1: "Centralized Bots" (Discord/Telegram bots)**
- Hypothesis: A bot on a central server can manage community knowledge.
- Reality: All messages routed through a third party. The bot operator sees everything. One subpoena and the community's private discussions are exposed.

**Wave 2: "Just Use ChatGPT"**
- Hypothesis: Members can copy-paste questions to external AI.
- Reality: Context is lost. Community knowledge stays fragmented. No automation, no memory, no integration with the chat flow.

**Wave 3: "Self-hosted AI"**
- Hypothesis: Run an LLM on your own server.
- Reality: Requires DevOps expertise, GPU hardware, and still creates a centralized chokepoint. Messages must leave the E2E encrypted channel to reach the server.

**Our hypothesis:** The missing piece is an agent that lives *inside* the Status protocol — using Waku for transport, the community's own infrastructure for inference, and the existing E2E encryption for privacy. No data leaves the community's control.

## Phases

### Phase 0: Foundation ✅ (current)

**Objective:** A working bot in a Status Community that responds to messages via cloud LLM. Prove the integration works.

**User flow:**
1. Bot starts, connects to status-backend
2. Logs into existing Status account (or creates one)
3. Joins a community, listens for messages
4. Any message → LLM response within seconds

**Tech:**
- Python 3.12+, uv
- status-backend (Go) via HTTP/WebSocket
- Anthropic API (Claude Sonnet)
- SOUL.md (identity) + MEMORY.md (long-term facts) as system prompt
- JSONL chat logs for conversation context

**Explicitly out of scope for Phase 0:**
- Local inference
- @mention filtering (responds to all messages)
- Multi-community support
- RAG / vector search
- Token-based context management
- Conversation summarization
- Admin commands
- Tests

**Outcome:** A functional bot that produces a "wow effect" — write a question, get a smart answer in seconds. Foundation for all subsequent phases.

---

### Phase 1: Context & Memory

**Objective:** Bot understands conversation history and community knowledge. Answers are contextual, not generic.

**Key features:**
- Token-based context window (not message count) with summarization when limit is reached
- Load chat history from status-backend on startup (not just from runtime logs)
- @mention filtering — respond only when addressed, or in designated channels
- Multi-user awareness — distinguish between community members
- Daily memory log — auto-generate `memory/YYYY-MM-DD.md` from significant interactions

**Tech:**
- `anthropic.count_tokens()` for precise token budgeting
- Conversation summarization via LLM when context exceeds threshold
- `wakuext_chatMessages` for historical context loading

**Outcome:** Bot feels like a participant who's been following the conversation, not a stateless Q&A machine.

---

### Phase 2: Knowledge Agent (RAG)

**Objective:** Bot builds and maintains a searchable knowledge base from community discussions. Answers recurring questions from indexed history.

**Key features:**
- Vector store for community messages and documents
- RAG pipeline: embed question → search → inject relevant context → answer
- "What did we decide about X?" queries
- Pinned knowledge — community admin can mark facts as canonical
- Source attribution — bot cites which message it's referencing

**Tech:**
- ChromaDB (embedded vector store)
- sentence-transformers for embeddings (or Anthropic embeddings API)
- SQLite for structured metadata

**Outcome:** Community has a living knowledge base that grows from organic discussion. New members can query the bot instead of scrolling months of chat.

---

### Phase 3: Local Inference

**Objective:** Replace cloud LLM with local inference. No user data leaves the community's control.

**Key features:**
- Ollama integration for local model serving
- Model selection (Llama, Mistral, Qwen — based on hardware)
- Fallback to cloud API if local model is unavailable
- Configurable privacy level: strict-local / hybrid / cloud-ok

**Tech:**
- Ollama API (HTTP, compatible with OpenAI format)
- Model quantization (4-bit for consumer hardware)

**Outcome:** Privacy-preserving architecture achieved. Community can run the full stack on a single machine with no external dependencies.

---

### Phase 4: Multi-Agent & Coordination

**Objective:** Multiple specialized agents working together in a community.

**Key features:**
- **Knowledge Agent** — answers questions from community knowledge base (Phase 2)
- **Coordinator Agent** — tracks decisions, action items, deadlines; generates weekly summaries
- **Onboarding Guide** — greets new members, walks through rules, connects to relevant people
- Agent-to-agent communication via internal protocol
- Community admin dashboard (web UI or Status chat commands)

**Tech:**
- Agent orchestration framework
- Shared memory/context between agents
- Role-based access control

**Outcome:** A community with AI-powered knowledge management, coordination, and onboarding — all running on the privacy-preserving Logos stack.

---

### Phase 5: Immutable Notes Integration

**Objective:** Connect agent's knowledge base with [Immutable Notes](https://github.com/logos-co/ideas/issues/13) — a decentralized encrypted notes manager on the Logos stack. Community knowledge becomes persistent, encrypted, and owned by the community.

**Key features:**
- **Shared vault:** Community knowledge base stored as an Immutable Notes vault — encrypted, synced via Waku, backed up to Codex
- **Agent as contributor:** Bot writes summaries, decisions, and FAQ entries directly into the shared vault
- **Agent as reader:** RAG pipeline (Phase 2) indexes the vault for answering questions
- **Member access:** Community members read/edit the vault in Immutable Notes app; agent sees updates in real-time via Waku sync
- **Keycard-gated access:** Vault decryption tied to community membership (same Keycard identity as Status account)

**Data flow:**
```
Community chat → Agent extracts knowledge → Writes to shared vault (Immutable Notes)
                                                    ↕ Waku sync
Community member → Opens vault in Immutable Notes → Reads/edits knowledge
                                                    ↕ Codex backup
                                            Permanent decentralized archive
```

**Tech:**
- Immutable Notes vault format (encrypted Markdown + SQLite)
- Waku topics for vault sync (same transport as Status messages)
- Codex API for long-term storage
- Shared encryption: community Keycard → vault key derivation

**Outcome:** Community knowledge is no longer trapped in chat history or in the agent's local files. It lives in a decentralized, encrypted vault that both humans and agents can read and write. The agent becomes a bridge between ephemeral chat and persistent knowledge.

---

### Phase 6: Full Logos Stack

**Objective:** Deep integration with the complete Logos ecosystem.

**Key features:**
- Nomos (Logos Blockchain) for agent identity, reputation, and governance
- Waku direct integration (bypass status-backend, talk to Waku natively)
- Multi-community federation — agents share knowledge across communities (with permissions)
- Payment integration — agent as Status account can receive/send crypto
- Agent marketplace — communities can discover and deploy agents

**Tech:**
- go-waku or nwaku bindings for Python
- Nomos for on-chain agent registry and reputation
- Status wallet integration for payments

**Outcome:** Fully decentralized AI agents that are native citizens of the Logos network. No centralized infrastructure. Community-owned, community-controlled intelligence.

## Risks

- **status-backend stability** — no official docs, no API guarantees. Must track status-go releases
- **Waku message delivery** — P2P networks have inherent latency and reliability trade-offs
- **Local inference quality** — smaller models produce worse answers than cloud models
- **Community adoption** — bot must provide clear value without being annoying
- **Cross-channel information leakage** — conversation context is per-channel (safe), but shared RAG index (Phase 2) or auto-extracted memory could leak private channel content into public channel answers. Mitigation: per-channel RAG index with access control, channel-tagged memory entries
- **Token economics** — if agent can hold crypto, security becomes critical
