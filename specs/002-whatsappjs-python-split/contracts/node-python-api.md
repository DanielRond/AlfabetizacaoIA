# Node -> Python API Contract

## Purpose

Define the internal HTTP contract between the Node WhatsApp connector and the Python processing backend.

## Inbound message request

### Endpoint

- **Method**: `POST`
- **Path**: `/v1/messages/inbound`
- **Content-Type**: `application/json`

### Payload fields

- `correlation_id`: shared trace identifier
- `message_id`: transport message identifier
- `phone_number`: sender number
- `message_type`: `text`, `audio`, `interactive`, `system`
- `text`: normalized text when available
- `media_ref`: file path, temporary URL, or storage key when media is present
- `received_at`: ISO timestamp
- `metadata`: optional transport metadata

### Required behavior

- The backend must accept normalized payloads from Node without assuming Meta webhook shapes.
- The backend must classify the message and decide the next action.
- The backend must not block on sending to WhatsApp.

## Response envelope

### Response fields

- `correlation_id`: same value sent by Node
- `action`: `send_text`, `send_audio`, `request_retry`, `noop`
- `text`: final text reply when relevant
- `media_ref`: generated artifact reference when relevant
- `media_type`: `audio`
- `status`: `ok`, `retry`, `error`
- `error_code`: optional structured failure code

### Required behavior

- The Node service must treat `action` as the source of truth for delivery.
- Large media must not be inlined as base64 in the normal happy path.
- `request_retry` must be used for unreadable audio or recoverable validation problems.

## Health check

- **Method**: `GET`
- **Path**: `/health`
- **Behavior**: return a simple JSON status for startup validation.

## Delivery acknowledgement

### Endpoint

- **Method**: `POST`
- **Path**: `/v1/messages/delivered`
- **Content-Type**: `application/json`

### Payload fields

- `correlation_id`: shared trace identifier (same value from the inbound message)
- `message_id`: transport message identifier
- `phone_number`: sender number
- `action`: the action that was dispatched (`send_text`, `send_audio`, ...)
- `status`: `delivered` or `failed`
- `media_ref`: optional media reference when the action was `send_audio`
- `delivered_at`: ISO timestamp
- `error`: optional failure message when `status` is `failed`

### Required behavior

- The Node service sends this after dispatching a response; it is fire-and-forget and must never fail the message pipeline.
- The backend must treat the endpoint as idempotent: it records/updates traceability records and always returns `200 {"status": "ok"}` for valid payloads.
- When `action` is `send_audio` and `status` is `delivered`, the backend marks the matching `MediaArtifact` as `sent`.