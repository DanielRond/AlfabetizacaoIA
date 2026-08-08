# 06 — Módulos do Conector Node

Código em `apps/whatsapp-connector/src/`. Todos os módulos em CommonJS (`'use strict'`),
Node 18+.

```text
src/
├── index.js        # Entrada: startup, health check, reconexão, shutdown
├── config.js       # Carregamento de env vars e defaults
├── logger.js       # Logger estruturado (pino)
├── session.js      # Cliente whatsapp-web.js, QR login, eventos
├── handlers.js     # Pipeline de uma mensagem recebida
├── normalizer.js   # Message → contrato interno
├── media.js        # Download/salvamento, resolução de media_ref, limpeza
├── apiClient.js    # HTTP client para o backend Python
└── sender.js       # Dispatch por action (envio de texto/áudio)
```

## `config.js` — Configuração central

- Carrega `.env` com prioridade: `apps/whatsapp-connector/.env` (1º) e depois o
  `.env` da raiz do repo (fallback em dev).
- Expõe um único objeto com todos os caminhos resolvidos para absolutos:
  - `pythonApiUrl` (`PYTHON_API_URL`, default `http://localhost:5000`);
  - `sessionDir` (`WHATSAPP_SESSION_DIR`, default `.wwebjs_auth` dentro do workspace);
  - `mediaDir` (`WHATSAPP_MEDIA_DIR`, default `data/media_in` na raiz do repo);
  - `mediaBaseDir` (`MEDIA_BASE_DIR`, default raiz do repo);
  - `mediaRetentionMs` (`MEDIA_RETENTION_HOURS` em horas → ms, default 24 h);
  - `browserPath` (`WHATSAPP_BROWSER_PATH`, opcional);
  - `logLevel`, `requestTimeoutMs` (default `120000`), `retries` (default `2`),
    `retryBaseDelayMs` (default `500`).

## `logger.js` — Log estruturado (pino)

- Pino em JSON para stdout, nível via `LOG_LEVEL`, `base: { service: 'whatsapp-connector' }`.
- `childLogger(bindings)` cria logger filho. No pipeline, o child carrega
  `correlation_id`, `message_id` e `phone_number` — toda linha do fluxo carrega o
  contexto sem repetição manual.

## `session.js` — Sessão WhatsApp

- `buildClient(onMessage)` cria o `Client` do whatsapp-web.js com:
  - `authStrategy: new LocalAuth({ dataPath: config.sessionDir })` — sessão persistida;
  - `puppeteer` com `headless: true` e `--no-sandbox`, e `executablePath` quando
    `config.browserPath` estiver definido (permite usar Brave/Chrome da máquina).
- Registra eventos: `qr` (imprime no terminal via `qrcode-terminal`), `authenticated`,
  `auth_failure`, `ready`, `change_state` (debug), `disconnected`.
- Evento `message`: chama `onMessage(client, message)` dentro de uma Promise tratada —
  erro de uma mensagem nunca derruba o processo.
- `module.exports = { buildClient }` — o `client` é passado ao handler como argumento,
  o que permite injetar mocks nos testes.

## `normalizer.js` — Contrato interno

- `classifyMessageType`: mapeia tipos do whatsapp-web.js para `text`, `audio`,
  `interactive`, `image` ou `system` (veja tabela no README do conector).
- `toDigits`: extrai só dígitos do número (`message.author || message.from`).
- `normalizeMessage(message)` retorna `null` para mensagens ignoradas:
  - `fromMe` (mensagens do próprio número);
  - tipos `protocol` / `e2e_notification`;
  - status de broadcast (`isStatus` ou `from === 'status@broadcast'`).
- Preenche o envelope do contrato e a flag interna `needsMedia` (não vai para o
  Python). Texto vazio sem mídia é reclassificado como `system`.
- `extractInteractiveText` extrai `selectedDisplayText` para respostas de listas/botões.

## `media.js` — Mídia de entrada e saída

- `saveInboundMedia(message, mediaDir)`: exige `message.downloadMedia()`, baixa a
  mídia (base64), garante o diretório, salva com nome `{timestamp}_{uuid8}{ext}` e
  retorna o **caminho absoluto**. Extensão derivada do mimetype (`audio/ogg` → `.ogg`).
- `resolveMediaRef(mediaBaseDir, mediaRef)`: resolve o caminho gerado pelo Python
  contra a base compartilhada; caminho absoluto é usado direto.
- `limparMediaAntiga(dir, maxAgeMs)`: remove arquivos com `mtimeMs` mais antigo que
  o limite (chamada no startup). Não lança se o diretório não existir.
- Utilitários exportados: `safeFilename`, `ensureDir`.

## `apiClient.js` — HTTP client para o Python

- `postInbound(payload, opts)`: POST `{PYTHON_API_URL}/v1/messages/inbound`.
  - Timeout via `AbortController` (`REQUEST_TIMEOUT_MS`);
  - retry com backoff exponencial (`base * 2^attempt`);
  - **4xx não são retentados** (`retryable: false` — erro de contrato);
  - **5xx/network/timeout** são retentados; após esgotar, lança o último erro.
- `postDelivered(payload, opts)`: POST `/v1/messages/delivered`, timeout curto (5 s),
  **sem retry**, fire-and-forget — nunca lança (retorna `null` em falha).
- `checkHealth(opts)`: GET `/health`, nunca lança (retorna `null` com backend fora).
- Testabilidade: `opts.fetchImpl` injeta a implementação de `fetch`.

## `sender.js` — Envio da resposta

- `dispatchResponse(client, target, response)` interpreta a `action` (fonte da
  verdade vinda do Python):

| `action` | Comportamento |
|---|---|
| `send_text` | `sendMessage` com `response.text` |
| `send_audio` | resolve `media_ref` → monta `MessageMedia('audio/ogg', base64, nome)` → `sendMediaAsVoice` |
| `request_retry` | envia `response.text` (pedido gentil) |
| `noop` / desconhecida | não faz nada |

- `sendAudio` aceita `opts.MessageMediaCtor` e `opts.readFile` injetáveis (testes não
  importam whatsapp-web.js nem leem disco real).

## `handlers.js` — Pipeline da mensagem

`handleInboundMessage(client, message)`:

1. `normalizeMessage`; se `null`, encerra.
2. Gera `correlation_id` (`randomUUID()`) e cria o child logger com o contexto.
3. Se `needsMedia`, `saveInboundMedia` → anexa `media_ref`.
4. `postInbound(normalized)` → loga `action`/`status`.
5. `dispatchResponse` para `message.from`.
6. `confirmDelivery(..., 'delivered', log)` — ack de sucesso.
7. **Catch**: loga, envia `FALLBACK_TEXT` ao aluno, `confirmDelivery(..., 'failed',
   log, err.message)` e retorna `null`.

`confirmDelivery` monta o payload do delivered (`correlation_id`, `message_id`,
`phone_number`, `action`, `status`, `media_ref`, `delivered_at` + `error` se houver)
e chama `postDelivered` — nunca lança.

## `index.js` — Ciclo de vida

- `main()`: `checkHealth()` (aviso se backend fora), depois `start()`.
- `start()`: `limparMediaAntiga(...)`, `buildClient`, registra `disconnected`,
  `client.initialize()`; zera o contador de tentativas ao conectar.
- `scheduleRestart(reason)`: backoff exponencial (base 5 s → teto 60 s), máx. 10
  tentativas; ao esgotar, `log.fatal` + `process.exit(1)`.
- `shutdown()`: `SIGINT`/`SIGTERM` → `shuttingDown = true`, limpa timer, destrói o
  cliente, `process.exit(0)`.

## Testes (42 no total, `node:test`)

| Arquivo | Cobre |
|---|---|
| `tests/normalizer.test.js` | Classificação, filtros, grupos, interativos, `needsMedia` |
| `tests/apiClient.test.js` | Payload, retry 5xx/rede, sem retry 4xx, `checkHealth`, `postDelivered` |
| `tests/media.test.js` | Salvamento, resolução de `media_ref`, `limparMediaAntiga` |
| `tests/sender.test.js` | Dispatch por action com mocks |
| `tests/handlers.test.js` | Pipeline com cliente mock: happy path + ack delivered, fallback + ack failed, ignorados |
| `tests/contract.test.js` | Conector contra as fixtures do contrato |

Estratégia de injeção: `opts.fetchImpl` (apiClient), `opts.MessageMediaCtor`/
`opts.readFile` (sender) e `client` como argumento (handlers).

## Próximos documentos

- [07-modulos-python.md](07-modulos-python.md) — o outro lado do contrato.
- [04-contrato-api.md](04-contrato-api.md) — a spec que esses módulos implementam.
