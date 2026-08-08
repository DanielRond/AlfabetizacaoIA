# 09 — Operação

## Variáveis de ambiente

### Backend Python (`.env.example` na raiz)

| Variável | Default | Descrição |
|---|---|---|
| `FLASK_ENV` | `development` | Ambiente Flask |
| `PORT` | `5000` | Porta do backend |
| `LOG_LEVEL` | `INFO` | Nível de log do Loguru |
| `IA_PROVIDER` | `ollama` | `ollama` ou `gemini` |
| `OLLAMA_API_URL` | `http://localhost:11434/api/generate` | URL do servidor Ollama |
| `OLLAMA_MODEL` | `llama3.2` | Modelo local |
| `GEMINI_API_KEY` | — | Chave da API Gemini |
| `GEMINI_MODEL` | `gemini-flash-latest` | Modelo Gemini |
| `TTS_ENABLED` | `true` | Liga/desliga a síntese de voz |
| `TTS_VOICE` | `pf_dora` | Voz do Kokoro |
| `KOKORO_MODEL_PATH` | `models/kokoro-v1.0.onnx` | Modelo ONNX do Kokoro |
| `KOKORO_VOICES_PATH` | `models/voices-v1.0.bin` | Vozes do Kokoro |
| `MEDIA_RETENTION_HOURS` | `24` | Retenção de mídia (TTS e entrada) em horas |

### Conector Node (`apps/whatsapp-connector/.env.example`)

| Variável | Default | Descrição |
|---|---|---|
| `PYTHON_API_URL` | `http://localhost:5000` | URL base do backend Python |
| `WHATSAPP_SESSION_DIR` | `.wwebjs_auth` | Diretório da sessão persistida (LocalAuth) |
| `WHATSAPP_BROWSER_PATH` | — | Caminho do navegador para o Puppeteer (ex.: Brave) |
| `WHATSAPP_MEDIA_DIR` | `data/media_in` | Diretório de mídia recebida |
| `MEDIA_BASE_DIR` | raiz do repo | Base para resolver `media_ref` do Python |
| `LOG_LEVEL` | `info` | Nível de log do pino |
| `REQUEST_TIMEOUT_MS` | `120000` | Timeout do POST inbound (ms) |
| `REQUEST_RETRIES` | `2` | Tentativas extras após 5xx/rede |
| `RETRY_BASE_DELAY_MS` | `500` | Atraso base do backoff exponencial (ms) |
| `MEDIA_RETENTION_HOURS` | `24` | Retenção da mídia de entrada (horas) |

O conector lê `.env` com prioridade: `apps/whatsapp-connector/.env` → `.env` da raiz.

## Setup

```bash
# Python
uv sync
cp .env.example .env

# Conector
cd apps/whatsapp-connector
npm install
cp .env.example .env
```

> **Dica npm**: pule o download do Chromium com `PUPPETEER_SKIP_DOWNLOAD=true` e
> aponte `WHATSAPP_BROWSER_PATH` para um navegador instalado (puppeteer-core).

> **Dica rede**: se o `npm install` falhar com `EACCES` (IPv6), use
> `export NODE_OPTIONS="--dns-result-order=ipv4first"`.

## Execução

```bash
# Terminal 1 — backend Python
uv run python -m curumim.main          # http://localhost:5000

# Terminal 2 — conector Node (QR na primeira execução)
cd apps/whatsapp-connector && npm start
# Desenvolvimento com auto-reload: npm run dev
```

Verificação rápida:

```bash
curl http://localhost:5000/health
```

### (Opcional) Popular o RAG

```bash
uv run python scripts/ingest_knowledge.py   # indexa data/knowledge/*.txt
```

## Testes

```bash
# Python unit (45 testes; não exige serviços externos)
.venv/bin/python -m pytest tests/ -q

# Python integração (4 testes; exige Ollama/Gemini, modelos e ChromaDB)
.venv/bin/python -m pytest tests/ -q -m integration

# Node (42 testes)
cd apps/whatsapp-connector && npm test
```

Config relevante no `pyproject.toml`: `addopts = ["-m", "not integration"]` faz o
pytest padrão rodar só unitários.

## Deploy (Gunicorn)

```bash
uv run gunicorn -c deploy/gunicorn_config.py "curumim.main:create_app()"
```

`deploy/gunicorn_config.py`: workers = `2 * núcleos + 1`, bind `0.0.0.0:5000`,
logs em `logs/gunicorn_{access,error}.log`.

O conector Node roda como processo separado (orquestrador pode reiniciá-lo após o
`process.exit(1)` de esgotamento de reconexão).

## Checklist de smoke test

1. Backend no ar → `GET /health` responde `healthy`.
2. Conector Node inicia → sessão WhatsApp estabelecida (QR na 1ª vez).
3. Enviar texto → resposta estruturada chega e o Node envia.
4. Enviar nota de voz → transcrição + resposta (e áudio se o nível exigir).
5. Áudio incompreensível → fallback `request_retry` gentil é entregue.
6. Ack de entrega → `InteractionRecord` outbound `sent` registrado no banco.

## Troubleshooting rápido

| Sintoma | Causa provável | Ação |
|---|---|---|
| Backend não responde | `.env` ausente ou porta ocupada | Conferir `.env`, `PORT` |
| `GEMINI_API_KEY não encontrada` | `.env` sem a chave / `IA_PROVIDER=gemini` | Definir chave no `.env` |
| Áudio de resposta nunca sai | Modelos Kokoro ausentes em `models/` | Baixar `.onnx` + `.bin` (ou `TTS_ENABLED=false`) |
| Transcrição falha | Parakeet não baixado / arquivo ausente | Checar `media_ref`, rede para o NGC |
| QR toda vez que inicia | `WHATSAPP_SESSION_DIR` fora do workspace | Ajustar variável |
| Testes de integração pulam | Provedor indisponível/ChromaDB vazio | Subir Ollama/Gemini, rodar ingestão |

## Observabilidade

- **Node**: pino → JSON em stdout. Filtrar por `correlation_id`.
- **Python**: Loguru → console + `logs/alfabot_*.log` (rotação diária, retenção 10 dias).
- **Banco**: `InteractionRecord` guarda payloads e status para reconstruir interações.
