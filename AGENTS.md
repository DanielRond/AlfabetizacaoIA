# AGENTS.md

Guia de contexto para agentes de IA que trabalham neste repositório. Leia antes de
fazer qualquer alteração. Para a documentação completa, veja [`docs/README.md`](docs/README.md).

## O que é este projeto

**Curumim Marajoara** é um tutor de alfabetização inteligente via WhatsApp, com IA
generativa (Ollama ou Gemini), RAG com conteúdo cultural marajoara (ChromaDB), STT
(NVIDIA Parakeet) e TTS local (Kokoro).

Arquitetura de **dois serviços independentes** que conversam por um contrato HTTP
versionado:

| Serviço | Runtime | Responsabilidade |
|---|---|---|
| `apps/whatsapp-connector` | Node.js (whatsapp-web.js) | Sessão WhatsApp, QR login, recepção, normalização, envio de respostas |
| `src/curumim` (backend) | Python 3 (Flask) | Perfil pedagógico, onboarding, RAG, STT, IA, TTS, rastreio |

O Node **não** conhece regras pedagógicas; o Python **não** fala diretamente com a Meta.

## Arquivos-chave

| Caminho | Papel |
|---|---|
| `src/curumim/main.py` | App Flask, endpoints `/v1/messages/inbound` e `/v1/messages/delivered`, lógica de onboarding e regras de áudio |
| `src/curumim/models/database.py` | SQLAlchemy: `LearnerProfile`, `ChatMessage`, `MediaArtifact`, `InteractionRecord`; migração idempotente |
| `src/curumim/services/ai_service.py` | Orquestra RAG + geração (Ollama/Gemini) |
| `src/curumim/services/rag_service.py` | ChromaDB (busca e ingestão de contexto) |
| `src/curumim/services/stt_service.py` | Transcrição de áudio (NeMo Parakeet, lazy-load) |
| `src/curumim/services/tts_service.py` | Síntese de voz (Kokoro), limpeza de artefatos antigos |
| `apps/whatsapp-connector/src/index.js` | Entrada: startup, health check, reconexão com backoff, shutdown |
| `apps/whatsapp-connector/src/handlers.js` | Pipeline de uma mensagem (normaliza → mídia → POST → envia → ack) |
| `apps/whatsapp-connector/src/normalizer.js` | Converte `Message` do whatsapp-web.js no contrato interno |
| `apps/whatsapp-connector/src/apiClient.js` | HTTP client p/ Python: `postInbound` (retry), `postDelivered`, `checkHealth` |
| `apps/whatsapp-connector/src/sender.js` | Dispatch por `action` (send_text/send_audio/request_retry/noop) |
| `specs/002-whatsappjs-python-split/contracts/node-python-api.md` | **Contrato Node→Python** (fonte da verdade da API) |
| `specs/002-whatsappjs-python-split/contracts/fixtures/` | Fixtures JSON usadas pelos testes de contrato |

## Comandos

```bash
# Testes Python (unitários; não exigem serviços externos)
.venv/bin/python -m pytest tests/ -q

# Testes de integração Python (Ollama/Gemini, TTS, RAG populado)
.venv/bin/python -m pytest tests/ -q -m integration

# Testes do conector Node
cd apps/whatsapp-connector && npm test

# Rodar backend Python
uv run python -m curumim.main          # http://localhost:5000

# Rodar conector Node (QR na primeira execução)
cd apps/whatsapp-connector && npm start

# Deploy conteinerizado (Docker Compose — deploy/Makefile)
make -C deploy up          # sobe backend + connector (QR na 1ª vez)
make -C deploy up-ollama   # ativa também o Ollama local (profile opcional)
```

Nenhuma alteração de código deve quebrar as suítes (45 Python + 42 Node).

## Convenções importantes

- **Idioma**: código, comentários, docs e commits em **português (PT-BR)**.
- **Nome do backend**: o pacote é `curumim` (não `alfabot`). O código vive em `src/curumim/`, não em `src/alfabot/`.
- **Banco real**: `src/data/curumim.db` (não `data/curumim.db` na raiz). `database.py` resolve `PROJECT_ROOT = Path(__file__).resolve().parents[2]` para `src/`.
- **Testes**: pytest (Python) e `node:test` (Node). Testes Node usam injeção de dependências (`opts.fetchImpl`, mocks de `client`).
- **Contrato**: a `action` do backend é a fonte da verdade para o envio no Node. `request_retry` = áudio incompreensível/erro recuperável. `error_code` é estruturado (ex.: `AUDIO_TRANSCRIPTION_FAILED`).
- **Rastreio**: `correlation_id` gerado no Node (UUID) acompanha a mensagem no payload, nos logs (Pino + Loguru) e em `InteractionRecord`.
- **Falhas**: `postDelivered` é fire-and-forget (nunca falha o pipeline). Backend fora não derruba o conector (retry por mensagem).
- **Segredos**: nunca commitar `.env`, tokens ou chaves. Usar `.env.example`.

## Documentação

- `docs/README.md` — índice da documentação
- `docs/01-visao-geral.md` — funcionalidades e estrutura
- `docs/02-arquitetura.md` — arquitetura e fronteiras
- `docs/03-fluxos.md` — fluxos ponta a ponta
- `docs/04-contrato-api.md` — contrato HTTP detalhado
- `docs/05-banco-de-dados.md` — modelo de dados
- `docs/06-modulos-node.md` — walkthrough do conector Node
- `docs/07-modulos-python.md` — walkthrough do backend Python
- `docs/08-decisoes.md` — decisões arquiteturais (ADRs)
- `docs/09-operacao.md` — env vars, execução, deploy, testes
