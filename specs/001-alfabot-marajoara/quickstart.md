# Quickstart: Alfabot Marajoara

## Prerequisites

- Python 3 installed and available through `uv`
- SQLite available locally through the Python runtime
- Ollama installed locally
- Hookdeck CLI installed for local webhook exposure during development

## Setup

```bash
uv sync
cp .env.example .env
```

Populate `.env` with the real Meta credentials and local runtime values.

## Local model setup

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

If the transcription model is not already available through Faster-Whisper caches, download or preinstall the CPU-ready Whisper model selected for the project.

## Run the application

```bash
uv run flask --app curumim.app run --host 0.0.0.0 --port 5000 --debug
```

## Expose the webhook locally

```bash
hookdeck listen 5000 webhook
```

Configure the Meta webhook URL to point to the Hookdeck forwarding URL and use the same `WHATSAPP_VERIFY_TOKEN` value configured in `.env`.

## Smoke test checklist

1. Send a verification request from Meta and confirm the webhook challenge succeeds.
2. Send a text message and confirm a level-aware reply is generated.
3. Send a voice note and confirm transcription, retrieval, and response dispatch complete.
4. Send an unreadable audio sample and confirm the bot asks for a new recording.

## Test suite

```bash
uv run pytest
```
