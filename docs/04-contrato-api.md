# 04 — Contrato API (Node → Python)

Fonte da verdade oficial: [`specs/002-whatsappjs-python-split/contracts/node-python-api.md`](../specs/002-whatsappjs-python-split/contracts/node-python-api.md).
Fixtures de exemplo: [`specs/002-whatsappjs-python-split/contracts/fixtures/`](../specs/002-whatsappjs-python-split/contracts/fixtures/).

## Endpoints

| Método | Caminho | Direção | Função |
|---|---|---|---|
| `POST` | `/v1/messages/inbound` | Node → Python | Processa uma mensagem normalizada e devolve a ação de resposta |
| `POST` | `/v1/messages/delivered` | Node → Python | Confirma entrega/falha da resposta (ack de rastreio) |
| `GET` | `/health` (e `/v1/health`) | Node → Python | Validação de saúde no startup |

## 1. POST /v1/messages/inbound

### Request

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `correlation_id` | string | ✅ | Rastreio compartilhado (UUID gerado no Node) |
| `message_id` | string | — | Id de transporte da mensagem |
| `phone_number` | string | ✅ | Remetente, apenas dígitos (ex.: `5591999999999`) |
| `message_type` | string | ✅ | `text`, `audio`, `interactive`, `image`, `system` |
| `text` | string | — | Texto normalizado (vazio quando há mídia) |
| `media_ref` | string | — | Caminho local da mídia salva pelo Node |
| `received_at` | string | — | Timestamp ISO da recepção |
| `metadata` | object | — | `chat_id` (id do chat), `from_me` |

Exemplo (fixture `inbound-message.json`):

```json
{
  "correlation_id": "8c7c1b4a-...",
  "message_id": "ABC123",
  "phone_number": "5591999999999",
  "message_type": "text",
  "text": "o que é a lenda do boto?",
  "media_ref": null,
  "received_at": "2026-08-07T20:18:00.000Z",
  "metadata": { "chat_id": "5591999999999@c.us", "from_me": false }
}
```

### Response (envelope)

| Campo | Tipo | Descrição |
|---|---|---|
| `correlation_id` | string | Ecoa o valor recebido |
| `action` | string | `send_text`, `send_audio`, `request_retry`, `noop`, `error` |
| `text` | string | Texto final quando relevante |
| `media_ref` | string | Artefato gerado quando `action == send_audio` |
| `media_type` | string | `audio` |
| `status` | string | `ok`, `retry`, `error` |
| `error_code` | string | Código estruturado de falha (null no happy path) |

Exemplo (fixture `processing-result.json`):

```json
{
  "correlation_id": "8c7c1b4a-...",
  "action": "send_text",
  "text": "O boto é uma lenda marajoara...",
  "media_ref": null,
  "media_type": null,
  "status": "ok",
  "error_code": null
}
```

### Ações e códigos de erro

| `action` | Quando | `status` | `error_code` |
|---|---|---|---|
| `send_text` | Resposta textual normal / recusa de imagem | `ok` | `null` |
| `send_audio` | Resposta com áudio (iniciantes/básico-áudio) | `ok` | `null` |
| `request_retry` | Áudio incompreensível ou arquivo ausente | `retry` | `AUDIO_TRANSCRIPTION_FAILED` / `MEDIA_FILE_NOT_FOUND` |
| `noop` | Texto vazio sem conteúdo processável | `ok` | `null` |
| `error` | Payload inválido / erro interno | `error` | `INVALID_JSON_PAYLOAD`, `MISSING_REQUIRED_FIELDS`, `INTERNAL_SERVER_ERROR` |

### Regras de negócio observadas

- `request_retry` **nunca** deve gerar resposta inventada: o aluno sempre recebe o
  pedido gentil de repetição.
- A `action` retornada é a **fonte da verdade** para o envio no Node
  (ver [`06-modulos-node.md`](06-modulos-node.md) → `sender.js`).

## 2. POST /v1/messages/delivered

### Request

| Campo | Tipo | Descrição |
|---|---|---|
| `correlation_id` | string | Mesmo valor do inbound |
| `message_id` | string | Id de transporte |
| `phone_number` | string | Remetente |
| `action` | string | Ação despachada (`send_text`, `send_audio`, …) |
| `status` | string | `delivered` ou `failed` |
| `media_ref` | string | Referência do artefato quando `action == send_audio` |
| `delivered_at` | string | Timestamp ISO |
| `error` | string | Mensagem de falha quando `status == failed` |

### Comportamento esperado

- Enviado pelo Node após o dispatch; é **fire-and-forget** e nunca falha o pipeline.
- Idempotente: payload válido sempre retorna `200 {"status": "ok"}`.
- Quando `action == send_audio` e `status == delivered`, o Python marca o
  `MediaArtifact` correspondente como `sent` (e grava `InteractionRecord` outbound).

### Respuestas HTTP

| Cenário | Código | Corpo |
|---|---|---|
| Payload válido | `200` | `{"status": "ok"}` |
| `correlation_id` ausente ou `status` inválido | `400` | `{"status": "error"}` |
| Perfil não encontrado | `200` | `{"status": "ok"}` (no-op) |

## 3. GET /health

Resposta `200`:

```json
{
  "status": "healthy",
  "service": "curumim-backend-python",
  "version": "1.0.0"
}
```

O conector usa apenas `status == "healthy"` para decidir se loga "backend saudável".
Se falhar/tempo esgotar, o conector continua (retry por mensagem).

## Fixtures de contrato

Usadas pelos testes de contrato (`tests/contract/test_contrato.py` e
`apps/whatsapp-connector/tests/contract.test.js`):

| Arquivo | Conteúdo |
|---|---|
| `inbound-message.json` | Payload de entrada normalizado |
| `processing-result.json` | Envelope de resposta do backend |
| `delivered.json` | Payload do ack de entrega |

## Próximos documentos

- [03-fluxos.md](03-fluxos.md) — como o contrato é usado em cada fluxo.
- [05-banco-de-dados.md](05-banco-de-dados.md) — como o delivered persiste o rastreio.
