# Implementation Plan: WhatsApp JS + Python Split

**Branch**: `development` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)

## Summary

Transformar a integracao atual em uma arquitetura com dois servicos: um Node service responsavel pela conexao WhatsApp baseada em sessao e pelo envio de mensagens, e um backend Python responsavel por processamento de mensagens, IA, RAG, transcricao e geracao de midia.

## Technical Context

**Language/Version**: Node.js para o conector WhatsApp e Python 3 para o backend de IA

**Primary Dependencies**: whatsapp.js / whatsapp-web.js style client, Flask, SQLAlchemy, SQLite, ChromaDB, Faster-Whisper, Ollama, requests, loguru, pytest, dotenv, and a Node HTTP client for the internal API

**Storage**: SQLite for learner state and interaction history; ChromaDB for vector retrieval; filesystem or shared storage for temporary media artifacts

**Testing**: pytest for the Python backend; Node test coverage for the relay and send pipeline; contract tests for the Node -> Python API

**Target Platform**: Two-process local deployment for development, with the Node process holding the WhatsApp session and the Python process exposing the internal processing API

**Project Type**: Split backend, with transport in Node and intelligence in Python

**Performance Goals**: Keep message relay low latency, keep Python processing bounded for short text messages, and avoid large payloads crossing the Node/Python boundary

**Constraints**: The WhatsApp transport must be session-based in Node; the Python service must not depend on the Meta Cloud API; secrets must stay in environment variables; audio and video should move through artifact references instead of large inline blobs

**Scale/Scope**: Single active chatbot instance for development, with a path to later multi-instance deployment if needed

## Constitution Check

**Status**: BLOCKED until the constitution is amended for the new multi-runtime architecture.

| Principle | Status | Notes |
|---|---|---|
| Python-only application stack | FAIL | The new design adds Node as a first-class runtime for the WhatsApp connector. |
| Explicit Meta API boundary | NEEDS UPDATE | The boundary moves from direct Meta requests to a Node session client and an internal API contract. |
| Secrets and logging discipline | PASS | Still applies across both services. |
| Pytest coverage for behavior changes | PASS | The touched slices can be covered with backend and contract tests. |
| Simplicity and local determinism | PASS WITH CAUTION | The split is justified by the transport/runtime boundary, but the contract must stay small. |

## Project Structure

### Documentation

```text
specs/002-whatsappjs-python-split/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    └── node-python-api.md
```

### Source Code Target Shape

```text
apps/
└── whatsapp-connector/
    ├── src/
    ├── package.json
    └── tests/

src/
└── alfabot/
    ├── app.py
    ├── services/
    ├── infra/
    └── prompts/
```

## Delivery Phases

### Phase 1: Contract and Environment Setup

Define the Node -> Python payloads, environment variables, and runtime folders for shared artifacts.

### Phase 2: Node Transport Layer

Implement the WhatsApp session client, inbound event normalization, reconnection handling, and outbound message dispatch in Node.

### Phase 3: Python Processing API

Expose the internal HTTP API in Python, accept normalized messages, run profile lookup, RAG, transcription, and response generation.

### Phase 4: Media Response Pipeline

Add artifact handoff for audio and video responses so Python can generate the media and Node can publish it.

### Phase 5: Hardening and Validation

Add contract tests, failure handling, and smoke tests for the end-to-end relay.

## Implementation Strategy

1. Freeze the Node/Python API contract first.
2. Build the Node connector to own login, receive, and send behavior.
3. Move the Python service to an internal processing API.
4. Add media artifact handoff for audio and video.
5. Finish with contract tests and a local development runbook.