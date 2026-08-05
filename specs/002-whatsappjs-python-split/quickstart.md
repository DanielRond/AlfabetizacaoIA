# Quickstart: WhatsApp JS + Python Split

## Prerequisites

- Node.js installed for the WhatsApp connector
- Python 3.11+ installed for the backend
- SQLite available locally through Python
- Ollama installed locally if the project keeps local generation
- Access to a WhatsApp account for QR session login

## Setup

```bash
uv sync
cp .env.example .env
```

Install Node dependencies in the connector workspace:

```bash
npm install
```

## Environment variables

Configure at least:

- `PYTHON_API_URL`
- `WHATSAPP_SESSION_DIR`
- `WHATSAPP_MEDIA_DIR`
- `OLLAMA_API_URL`
- `OLLAMA_MODEL`
- `GEMINI_API_KEY` if applicable

## Run the backend

```bash
uv run python -m src.alfabot.main
```

## Run the WhatsApp connector

```bash
npm run dev
```

The first startup should prompt for QR login in the Node process.

## Smoke test checklist

1. Start the Python backend and confirm the health endpoint responds.
2. Start the Node connector and confirm a WhatsApp session is established.
3. Send a text message and confirm the backend returns a structured response and the Node sends it.
4. Send an audio note and confirm transcription and reply generation work.
5. Trigger an unreadable audio sample and confirm the fallback retry message is delivered.

## Test suite

```bash
uv run pytest
```

Run the Node test commands defined in the connector package after the API contract is in place.