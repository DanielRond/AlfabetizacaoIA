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
- `message_type`: `text`, `audio`, `video`, `interactive`, `system`
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
- `action`: `send_text`, `send_audio`, `send_video`, `request_retry`, `noop`
- `text`: final text reply when relevant
- `media_ref`: generated artifact reference when relevant
- `media_type`: `audio` or `video`
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