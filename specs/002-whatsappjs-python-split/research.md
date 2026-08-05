# Research Notes: WhatsApp JS + Python Split

## 1. WhatsApp transport ownership

**Decision**: Let the Node service own the WhatsApp session, QR login, message receipt, reconnection, and sending.

**Rationale**: A session-based WhatsApp client fits better in Node and keeps the transport boundary away from the Python AI stack.

**Alternatives considered**:
- Keeping the current Meta Cloud API webhook path, rejected because the new requirement removes the direct Meta integration from the Python backend.
- Moving WhatsApp handling into Python through another wrapper, rejected because the transport concern is better isolated in Node.

## 2. Internal API boundary

**Decision**: Use a small HTTP API from Node to Python with a versioned request and response envelope.

**Rationale**: HTTP keeps the boundary simple, debuggable, and easy to test locally without introducing a message broker too early.

**Alternatives considered**:
- A queue-based design, rejected for the first iteration because it adds operational overhead and makes local development harder.
- Direct process-to-process calls, rejected because they make the two services harder to deploy and observe independently.

## 3. Media handoff for audio and video

**Decision**: Pass media as artifact references instead of large inline payloads.

**Rationale**: Audio and video are too large for a clean JSON boundary in normal use. A file path, temporary URL, or storage key is easier to retry and inspect.

**Alternatives considered**:
- Base64 in JSON, rejected because it inflates payload size and complicates retries.
- Streaming the file through the API, rejected for the first pass because it adds complexity to both services.

## 4. Python backend responsibilities

**Decision**: Keep profile lookup, pedagogy, RAG, transcription, prompt building, and artifact generation in Python.

**Rationale**: This preserves the existing AI codebase and keeps the domain logic in one place.

**Alternatives considered**:
- Splitting AI logic into Node, rejected because it would duplicate the existing Python stack and increase maintenance.

## 5. Testing boundaries

**Decision**: Add contract tests for the Node -> Python API and targeted tests for both the connector and the backend.

**Rationale**: The new failure modes are mostly at the boundary, so contract tests give the best signal per effort.

**Alternatives considered**:
- Only end-to-end tests, rejected because they are slower and make boundary regressions harder to isolate.