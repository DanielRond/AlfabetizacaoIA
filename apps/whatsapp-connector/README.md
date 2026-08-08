# WhatsApp Connector (Node.js)

O **whatsapp-connector** é o serviço Node.js do **Curumim Marajoara** responsável por toda a comunicação com o WhatsApp. Ele mantém a sessão ativa (login via QR code), recebe mensagens, normaliza os eventos para um contrato interno estável e repassa ao backend Python — que fica responsável pelo processamento de IA, RAG, transcrição e geração de respostas.

A separação de responsabilidades está definida na spec [`specs/002-whatsappjs-python-split/spec.md`](../../specs/002-whatsappjs-python-split/spec.md) e o contrato HTTP entre os serviços em [`specs/002-whatsappjs-python-split/contracts/node-python-api.md`](../../specs/002-whatsappjs-python-split/contracts/node-python-api.md).

---

## 1. Visão geral da arquitetura

O conector é a única ponte entre o WhatsApp e o backend Python. O Node **não** conhece regras pedagógicas; o Python **não** fala diretamente com a Meta.

```text
        +-------------------+       WhatsApp / Meta
        |   Telefone        |            |
        +-------------------+            |
                 ^                       v
                 |             +---------------------+
                 |             |   whatsapp-web.js   |
                 |             |   (Puppeteer)       |
                 |             +---------------------+
                 |                       |
        envio de resposta         evento `message`
        (texto/áudio)                   |
                 |                       v
                 |            +---------------------+
                 |            |   session.js        |  QR login, LocalAuth
                 |            +---------------------+
                 |                       |
                 |                       v
                 |            +---------------------+
                 |            |   normalizer.js     |  contrato interno
                 |            +---------------------+
                 |                       |
                 |                       v (mídia)
                 |            +---------------------+
                 |            |   media.js          |  baixa e salva
                 |            +---------------------+
                 |                       |
                 |                       v
                 |            +---------------------+   POST /v1/messages/inbound
                 |            |   apiClient.js      | + retry + timeout
                 |            +---------------------+
                 |                       |
                 |                       v
                 |            +---------------------+   backend Python
                 |            |   Flask (curumim)   |   (IA, RAG, STT, TTS)
                 |            +---------------------+
                 |                       |
                 |   envelope de resposta (action, text, media_ref)
                 |                       |
                 +-----------------------v
                     +---------------------+
                     |   sender.js         |  dispatch por `action`
                     +---------------------+
```

O fluxo é coordenado por `handlers.js`, que orquestra as etapas de uma mensagem recebida. O `correlation_id` é gerado uma única vez e acompanha a mensagem por todos os logs do pipeline, permitindo correlacionar o evento do WhatsApp ao processamento no Python e ao envio final.

---

## 2. Estrutura de arquivos

```text
apps/whatsapp-connector/
├── src/
│   ├── index.js        # Ponto de entrada: startup, health check, reconexão, shutdown
│   ├── config.js       # Carregamento de variáveis de ambiente e defaults
│   ├── logger.js       # Logger estruturado (pino)
│   ├── session.js      # Cliente whatsapp-web.js, QR login e eventos de sessão
│   ├── handlers.js     # Orquestra o pipeline de uma mensagem recebida
│   ├── normalizer.js   # Converte Message do whatsapp-web.js no contrato interno
│   ├── media.js        # Download/salvamento de mídia e resolução de media_ref
│   ├── apiClient.js    # HTTP client para o backend Python (POST/health + retry)
│   └── sender.js       # Envio das respostas (texto, áudio) conforme a action
├── tests/
│   ├── apiClient.test.js   # Retry, timeout e comportamento HTTP
│   ├── media.test.js       # Salvamento e resolução de mídia
│   ├── normalizer.test.js  # Classificação e normalização de mensagens
│   └── sender.test.js      # Dispatch por action e envio de texto/áudio
├── package.json
├── package-lock.json
├── .env.example
└── .gitignore
```

---

## 3. Módulos em detalhe

### 3.1 `src/config.js` — Configuração central

Reúne todas as variáveis de ambiente do conector em um único objeto, com valores padrão seguros.

**Carregamento do `.env`** (com prioridade):

1. `apps/whatsapp-connector/.env` — ambiente local do conector (maior prioridade);
2. `.env` da raiz do repositório — configuração compartilhada em desenvolvimento.

**Variáveis lidas** (detalhadas na [seção 6](#6-variáveis-de-ambiente)): `PYTHON_API_URL`, `WHATSAPP_SESSION_DIR`, `WHATSAPP_MEDIA_DIR`, `MEDIA_BASE_DIR`, `LOG_LEVEL`, `REQUEST_TIMEOUT_MS`, `REQUEST_RETRIES` e `RETRY_BASE_DELAY_MS`.

Os caminhos são resolvidos de forma absoluta a partir do diretório do workspace, evitando dependência do diretório corrente de execução.

### 3.2 `src/logger.js` — Log estruturado

Usa [pino](https://github.com/pinojs/pino) com:

- `base: { service: 'whatsapp-connector' }` — identifica a origem do log;
- `timestamp` ISO — rastreio temporal das interações;
- nível configurável via `LOG_LEVEL` (default `info`).

A função `childLogger(bindings)` cria um logger filho. No pipeline de mensagem, o child é criado com `correlation_id`, `message_id` e `phone_number`, então **toda** linha de log daquele fluxo carrega o identificador de correlação sem repetição manual.

### 3.3 `src/session.js` — Sessão WhatsApp

Cria e configura a instância de `Client` do `whatsapp-web.js`.

**Configuração do cliente:**

```js
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: config.sessionDir }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});
```

- **`LocalAuth`** persiste a sessão no diretório `WHATSAPP_SESSION_DIR` (default `.wwebjs_auth`). Assim, reinícios do processo não exigem novo login — apenas a primeira execução pede QR code.
- **`puppeteer.headless`** roda o Chromium em background, sem janela visível. Os argumentos `--no-sandbox` e `--disable-setuid-sandbox` são necessários em ambientes containerizados/CI.

**Eventos registrados:**

| Evento | Comportamento |
|---|---|
| `qr` | Gera o QR code no terminal via `qrcode-terminal` para o login do usuário. |
| `authenticated` | Sessão autenticada no WhatsApp. |
| `auth_failure` | Falha de autenticação (sessão inválida/revogada) — apenas loga. |
| `ready` | Cliente pronto para receber mensagens. |
| `change_state` | Mudança de estado da conexão — loga em nível `debug`. |
| `disconnected` | Conexão encerrada — tratado em `index.js` para agendar reconexão. |
| `message` | Nova mensagem recebida — dispara `onMessage(client, message)` em uma Promise tratada, evitando que um erro de uma mensagem derrube o processo. |

### 3.4 `src/normalizer.js` — Normalização para o contrato

Converte um `Message` do `whatsapp-web.js` (estrutura dependente da biblioteca) no payload normalizado exigido pelo backend Python. É a garantia de que o Python nunca precisa conhecer a estrutura interna do whatsapp-web.js.

**Mapeamento de tipos** (`classifyMessageType`):

| Tipo WhatsApp | Tipo interno (`message_type`) |
|---|---|
| `text`, `chat` | `text` |
| `audio`, `ptt` | `audio` |
| `button`, `interactive`, `list_response`, `template`, `list` | `interactive` |
| `image`, `video`, `document`, `sticker` | `image` |
| `call_log`, `vcard`, `location`, `revoked` | `system` |
| `protocol`, `e2e_notification` | **ignorado** (retorna `null`) |

> **Nota:** o tipo `image` (mídia não suportada pelo backend) é normalizado e enviado; o backend Python decide a recusa amigável. O `needsMedia` fica `true` e o conector baixa e anexa o `media_ref`.

**Filtros** — mensagens que retornam `null` e não geram processamento:

- mensagens do próprio usuário (`fromMe`);
- tipos de protocolo/criptografia (`protocol`, `e2e_notification`);
- status de broadcast (`isStatus` ou `from === 'status@broadcast'`).

**Campos gerados:**

- `message_id` — id do transporte (`message.id.id`);
- `phone_number` — apenas dígitos de `message.author || message.from` (ex.: `5511999999999`);
- `message_type` — tipo normalizado;
- `text` — texto limpo (`trim()`), vazio quando há mídia;
- `media_ref` — preenchido depois por `handlers.js` quando `needsMedia` é `true`;
- `received_at` — timestamp convertido para ISO 8601;
- `metadata.chat_id` — id completo do chat (útil para grupos);
- `needsMedia` — flag de controle interno (não faz parte do contrato enviado ao Python).

**Casos especiais:**

- **Grupos**: `message.author` identifica o remetente real; `message.from` vira `metadata.chat_id`.
- **Mensagens interativas** (`list_response`): o texto é extraído de `selectedDisplayText`, que carrega a opção escolhida pelo aluno.
- **Texto vazio sem mídia**: reclassificado como `system` — não há o que processar.

### 3.5 `src/handlers.js` — Orquestração do pipeline

Função `handleInboundMessage(client, message)` chamada pelo evento `message`. Sequência:

```text
normalizeMessage → gera correlation_id → (se needsMedia) saveInboundMedia
  → postInbound (API Python) → dispatchResponse (envio no WhatsApp)
  → postDelivered (ack de entrega)
```

1. **Normaliza** a mensagem; se for `null`, encerra sem efeito.
2. **Gera `correlation_id`** via `randomUUID()` e cria o logger filho com o contexto de rastreio.
3. **Baixa a mídia** (`saveInboundMedia`) quando `needsMedia`, salvando o arquivo em disco e anexando `media_ref`.
4. **Envia ao Python** (`postInbound`) e loga a `action`/`status` da resposta.
5. **Despacha a resposta** para o WhatsApp (`dispatchResponse`) com destino `message.from`.
6. **Confirma a entrega** (`postDelivered`) ao backend — fire-and-forget, nunca derruba o pipeline:
   - sucesso → `status: "delivered"`;
   - falha no pipeline/fallback → `status: "failed"` (com `error`).
7. **Fallback**: qualquer erro no pipeline é logado e o aluno recebe a mensagem gentil:

```js
const FALLBACK_TEXT = 'Tive um probleminha para processar sua mensagem. Pode tentar de novo?';
```

A função `module.exports` recebe o `client` no evento de `session.js` — isso permite que os testes do pipeline injetem um cliente mock.

### 3.6 `src/media.js` — Mídia de entrada e saída

**Entrada — `saveInboundMedia(message, mediaDir)`:**

1. Exige `message.downloadMedia()`;
2. Baixa a mídia (base64) e converte para `Buffer`;
3. Cria o diretório se necessário;
4. Salva com nome único `{timestamp}_{uuid}.{extensão do mimetype}`;
5. Retorna o **caminho absoluto** do arquivo salvo.

A extensão é derivada do `mimetype` (ex.: `audio/ogg` → `.ogg`). Arquivos são gravados em `WHATSAPP_MEDIA_DIR` (default `data/media_in` na raiz do repo), de onde o backend Python os lê para transcrição/processamento.

**Saída — `resolveMediaRef(mediaBaseDir, mediaRef)`:**

Resolve a referência de mídia gerada pelo backend contra a base compartilhada (`MEDIA_BASE_DIR`). Se `media_ref` for absoluto, usa direto; senão, resolve contra a base. É o mecanismo que permite ao Python publicar artefatos (ex.: áudios em `data/audios`) para o Node entregar.

**Limpeza — `limparMediaAntiga(dir, maxAgeMs)`:**

Remove arquivos de mídia de entrada com `mtimeMs` mais antigo que `maxAgeMs` (default `MEDIA_RETENTION_HOURS` = 24 h). É chamada no `start()` de `index.js`, antes de `client.initialize()`, evitando acúmulo de mídia antiga no disco.

### 3.7 `src/apiClient.js` — Cliente HTTP do backend Python

Encapsula a comunicação com o backend com resiliência embutida.

**`postInbound(payload, opts)` — `POST {PYTHON_API_URL}/v1/messages/inbound`:**

- Envia o payload normalizado como JSON;
- **Timeout** via `AbortController` (`REQUEST_TIMEOUT_MS`, default `120000`);
- **Retry com backoff exponencial** (`REQUEST_RETRIES`, default `2`, e `RETRY_BASE_DELAY_MS`, default `500`):
  - Erros **4xx** não são retentados (`retryable: false`) — é erro de contrato/payload;
  - Erros **5xx**, de rede ou timeout são retentados com atraso `base * 2^attempt`;
  - Resposta `ok` (2xx) é parseada como JSON.
- Após esgotar as tentativas, lança o último erro com `status` e corpo, para o `handlers` tratar.

**`checkHealth(opts)` — `GET {PYTHON_API_URL}/health`:**

- Verifica o backend na inicialização;
- Nunca lança exceção: retorna `null` quando o backend está fora, para o conector continuar e fazer retry por mensagem.

**`postDelivered(payload, opts)` — `POST {PYTHON_API_URL}/v1/messages/delivered`:**

- Confirma a entrega da resposta ao backend (ack de rastreio ponta a ponta);
- Timeout curto (5 s), **sem retry**, fire-and-forget: nunca lança exceção (retorna `null` em falha);
- Enviado por `handlers.js` após o dispatch, com `status: "delivered"` (sucesso) ou `"failed"` (falha no pipeline).

**Testabilidade:** `opts.fetchImpl` injeta o `fetch` usado (os testes fornecem um fake), sem depender de rede real.

### 3.8 `src/sender.js` — Envio das respostas

`dispatchResponse(client, target, response)` interpreta o envelope do backend Python e executa a entrega. A **`action` vinda do Python é a fonte da verdade** para o envio.

| `action` | Comportamento |
|---|---|
| `send_text` | Envia `response.text` como mensagem de texto. |
| `send_audio` | Lê o arquivo resolvido por `resolveMediaRef`, monta um `MessageMedia` (`audio/ogg`) e envia como **nota de voz** (`sendMediaAsVoice`). |
| `request_retry` | Envia o `response.text` (pedido gentil de novo envio, ex.: áudio incompreensível). |
| `noop` | Não faz nada (fallback para ações desconhecidas). |

Em `sendAudio`, `MessageMediaCtor` e `readFile` são injetáveis via `opts`, permitindo que os testes evitem importar o `whatsapp-web.js` de verdade.

### 3.9 `src/index.js` — Ponto de entrada e ciclo de vida

**Startup (`main`):**

1. Chama `checkHealth()` — loga "Backend Python saudável" ou apenas um aviso (sem abortar);
2. `start()` executa `limparMediaAntiga(config.mediaDir, config.mediaRetentionMs)` (limpeza de mídia antiga), cria o cliente, registra o evento `disconnected` e inicializa a sessão;
3. Loga que o conector está pronto.

**Reconexão (`scheduleRestart`):**

- Ao `disconnected`, destrói o cliente e agenda a reconexão com **backoff exponencial**:
  - base `5s`, dobro a cada tentativa, teto `60s`;
  - máximo de `10` tentativas consecutivas;
- A cada nova conexão bem-sucedida, o contador de tentativas é zerado;
- Após exceder as tentativas, loga `fatal` e encerra com `process.exit(1)` — para permitir recuperação por orquestrador (Docker/systemd/PM2).

**Shutdown gracioso:**

- `SIGINT` (Ctrl+C) e `SIGTERM` chamam `shutdown()`:
  - impede novas reconexões (`shuttingDown`);
  - limpa o timer de reconexão pendente;
  - destrói a sessão WhatsApp;
  - encerra com `process.exit(0)`.

---

## 4. Fluxo ponta a ponta de uma mensagem

Exemplo prático: um aluno envia "o que é a lenda do boto?" como texto.

1. `whatsapp-web.js` emite `message`.
2. `session.js` chama `handleInboundMessage(client, message)`.
3. `normalizer.js` produz:
   ```json
   {
     "message_id": "ABC123",
     "phone_number": "5591999999999",
     "message_type": "text",
     "text": "o que é a lenda do boto?",
     "media_ref": null,
     "received_at": "2026-08-07T20:18:00.000Z",
     "metadata": { "chat_id": "5591999999999@c.us", "from_me": false }
   }
   ```
4. `handlers.js` adiciona `correlation_id` e faz `POST /v1/messages/inbound`.
5. O Python processa (perfil do aluno, RAG, IA) e responde:
   ```json
   {
     "correlation_id": "...",
     "action": "send_text",
     "text": "O boto é uma lenda marajoara sobre um boto que vira um moço bonito...",
     "status": "ok"
   }
   ```
6. `sender.js` executa `send_text` e entrega a resposta ao aluno.
7. Toda a cadeia é logada com o mesmo `correlation_id`.

### Fluxo com áudio

1. Aluno envia nota de voz (tipo `ptt`, `hasMedia: true`).
2. `normalizer.js` → `message_type: "audio"`, `needsMedia: true`.
3. `media.js` baixa e salva o `.ogg` em `data/media_in`.
4. Payload segue com `media_ref` preenchido.
5. Python transcreve, gera resposta e (para iniciantes) cria um áudio de reforço.
6. Python responde `action: "send_audio"` com `media_ref` para o arquivo gerado.
7. `sender.js` resolve o caminho, monta `MessageMedia` e envia como nota de voz.

---

## 5. Contrato com o backend Python

Resumo do contrato definido em [`contracts/node-python-api.md`](../../specs/002-whatsappjs-python-split/contracts/node-python-api.md).

**Request — `POST /v1/messages/inbound`:**

| Campo | Tipo | Descrição |
|---|---|---|
| `correlation_id` | string | Identificador de rastreio compartilhado. |
| `message_id` | string | Id de transporte da mensagem. |
| `phone_number` | string | Número do remetente (apenas dígitos). |
| `message_type` | string | `text`, `audio`, `interactive`, `system` (e `image`). |
| `text` | string | Texto normalizado, quando houver. |
| `media_ref` | string | Caminho/chave da mídia, quando houver. |
| `received_at` | string | Timestamp ISO da recepção. |
| `metadata` | object | Metadados opcionais de transporte (`chat_id`, `from_me`). |

**Response:**

| Campo | Tipo | Descrição |
|---|---|---|
| `correlation_id` | string | Ecoa o valor enviado. |
| `action` | string | `send_text`, `send_audio`, `request_retry`, `noop`. |
| `text` | string | Texto final quando relevante. |
| `media_ref` | string | Artefato gerado quando relevante. |
| `media_type` | string | `audio`. |
| `status` | string | `ok`, `retry`, `error`. |
| `error_code` | string | Código estruturado de falha (opcional). |

**Regras do contrato que o Node observa:**

- A `action` é a fonte da verdade para o envio;
- `request_retry` é usado para áudio incompreensível ou erros recuperáveis;
- Mídia grande não é embutida em base64 no corpo da resposta normal (usa `media_ref`).

---

## 6. Variáveis de ambiente

Configuração completa em `.env.example`.

| Variável | Default | Descrição |
|---|---|---|
| `PYTHON_API_URL` | `http://localhost:5000` | URL base do backend Python (API interna). |
| `WHATSAPP_SESSION_DIR` | `.wwebjs_auth` | Diretório da sessão persistida (`LocalAuth`). |
| `WHATSAPP_MEDIA_DIR` | `data/media_in` | Diretório onde a mídia recebida é salva. |
| `MEDIA_BASE_DIR` | raiz do repo | Base para resolver `media_ref` gerado pelo Python. |
| `MEDIA_RETENTION_HOURS` | `24` | Retenção de mídia em horas; remove mídia de entrada mais antiga que o limite. |
| `LOG_LEVEL` | `info` | Nível de log (`trace` a `fatal`). |
| `REQUEST_TIMEOUT_MS` | `120000` | Timeout HTTP para o POST ao backend (ms). |
| `REQUEST_RETRIES` | `2` | Tentativas extras após falha de rede/5xx. |
| `RETRY_BASE_DELAY_MS` | `500` | Atraso base do backoff exponencial (ms). |

---

## 7. Resiliência e tratamento de falhas

| Cenário | Comportamento |
|---|---|
| Backend fora no startup | Health retorna `null`; conector continua e faz retry por mensagem. |
| Backend fora no processamento | `postInbound` tenta `REQUEST_RETRIES` vezes com backoff; se falhar, aluno recebe fallback gentil. |
| Falha no ack de entrega | `postDelivered` é fire-and-forget: falha é apenas logada, o pipeline não é afetado. |
| Erro 4xx do backend | Sem retry (erro de payload/contrato); fallback gentil ao aluno. |
| Timeout ou erro de rede | Retry com backoff exponencial. |
| WhatsApp desconectado | Reconexão automática com backoff (5s → 60s, máx. 10 tentativas) e `process.exit(1)` se esgotar. |
| Áudio incompreensível | Backend responde `request_retry`; Node entrega o texto de pedido de novo envio. |
| Mídia sem `downloadMedia` | Erro tratado no pipeline; fallback gentil. |
| Mídia antiga no disco | `limparMediaAntiga` remove no startup conforme `MEDIA_RETENTION_HOURS`. |
| Erro ao enviar fallback | Apenas loga o erro (não derruba o processo). |
| `SIGINT`/`SIGTERM` | Shutdown gracioso: cancela reconexão, destrói sessão, exit 0. |

---

## 8. Logs e correlação

Todos os logs usam pino (JSON em stdout). O contexto padrão:

- `service: "whatsapp-connector"`;
- no pipeline de mensagem, também `correlation_id`, `message_id` e `phone_number`.

**Exemplo de rastreio:**

```json
{"level":30,"time":"2026-08-07T20:18:00.000Z","service":"whatsapp-connector","correlation_id":"abc...","message_id":"ABC123","phone_number":"5591999999999","message_type":"text","msg":"Mensagem recebida do WhatsApp"}
{"level":30,"time":"...","correlation_id":"abc...","action":"send_text","status":"ok","msg":"Resposta do backend Python recebida"}
{"level":30,"time":"...","correlation_id":"abc...","action":"send_text","msg":"Resposta despachada para o WhatsApp"}
```

Usar o `correlation_id` permite cruzar esses eventos com o processamento no Loguru (Python) e reconstruir a interação de ponta a ponta.

---

## 9. Testes

Os testes usam o runner nativo do Node (`node:test`) e `node:assert/strict`:

```bash
npm test
```

**Suites e cobertura:**

| Arquivo | O que cobre |
|---|---|
| `tests/normalizer.test.js` | Classificação de tipos, extração de dígitos, filtros (fromMe/status/protocol), grupos, interativos, `needsMedia`. |
| `tests/apiClient.test.js` | Envio do payload correto, retry em 5xx/rede, ausência de retry em 4xx, esgotamento de tentativas, `checkHealth` com backend fora/ok, `postDelivered` (envio do payload, não lança em falha). |
| `tests/media.test.js` | Salvamento da mídia, resolução de `media_ref` e limpeza de mídia antiga (`limparMediaAntiga`). |
| `tests/sender.test.js` | Dispatch por `action` (texto, áudio, `request_retry`, `noop`). |
| `tests/handlers.test.js` | Pipeline com dependências mockadas: fluxo feliz + ack `delivered`, fallback + ack `failed`, mensagens ignoradas. |
| `tests/contract.test.js` | Valida o conector contra as fixtures do contrato (`specs/.../contracts/fixtures/`). |

**Estratégia de injeção de dependências** (usada pelos testes):

- `apiClient`: `opts.fetchImpl` substitui o `fetch` global;
- `sender`: `opts.MessageMediaCtor` e `opts.readFile` evitam importar `whatsapp-web.js`/disco real;
- `handler`: o `client` é passado como argumento, permitindo mocks no teste de pipeline.

---

## 10. Comandos e operação

```bash
# Desenvolvimento (reinicia a cada mudança)
npm run dev

# Produção / execução simples
npm start

# Testes
npm test
```

**Dica de instalação:** ao rodar `npm install`, o download do Chromium pode ser pulado com `PUPPETEER_SKIP_DOWNLOAD=true`. Nesse caso, o conector usa o Chrome instalado na máquina via `puppeteer-core`.

> **Nota (ambiente de desenvolvimento):** se a rede bloquear IPv6, o `npm install` pode falhar com `EACCES` ao conectar em `registry.npmjs.org`. Solução: forçar a resolução DNS por IPv4 adicionando no perfil do shell (`~/.bashrc`, `~/.zshrc`):
>
> ```bash
> export NODE_OPTIONS="--dns-result-order=ipv4first"
> ```
>
> Em deploy (Docker/container) isso normalmente não é necessário, pois o container já resolve o DNS pela stack do Docker.

**Primeira execução:** o processo exibe um QR code no terminal. Escaneie com o WhatsApp Web do telefone vinculado. Nas execuções seguintes a sessão é restaurada de `WHATSAPP_SESSION_DIR` sem novo login.

**Dependência dos serviços:** o conector precisa do backend Python em execução para processar mensagens, mas não falha ao iniciar se ele estiver fora — a resiliência é tratada por mensagem (veja [seção 7](#7-resiliência-e-tratamento-de-falhas)).
