# Tasks: WhatsApp JS + Python Split

**Input**: Documents from `/specs/002-whatsappjs-python-split/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup and Contract

**Goal**: Define the split architecture, environment variables, and the first version of the Node -> Python contract.

- [ ] T001 Create the new spec folder and align the branch goals in spec.md, plan.md, research.md, data-model.md, quickstart.md, and contracts/node-python-api.md
- [ ] T002 Define the internal API request and response envelope between Node and Python
- [ ] T003 Add environment variables for Python API URL, WhatsApp session storage, and shared media storage
- [ ] T004 Decide the local artifact flow for audio and video replies

## Phase 2: Node Transport Layer

**Goal**: Make the Node service own login, inbound relay, and outbound sending.

- [ ] T005 Initialize the Node connector workspace and runtime scripts
- [ ] T006 Implement WhatsApp session management and QR login flow
- [ ] T007 Normalize inbound text, audio, video, and interactive replies into the internal contract
- [ ] T008 Implement outbound send logic for text, audio, and video responses

## Phase 3: Python Processing API

**Goal**: Move message processing, RAG, transcription, and response generation behind an internal HTTP API.

- [ ] T009 Add the Python endpoint that receives normalized inbound messages
- [ ] T010 Reuse learner profile lookup and onboarding state in the new API path
- [ ] T011 Keep the text, audio, and RAG pipeline in Python
- [ ] T012 Return structured ProcessingResult payloads to Node

## Phase 4: Media Pipeline

**Goal**: Allow Python to generate audio or video replies while Node delivers the final media.

- [ ] T013 Define media artifact generation and cleanup rules
- [ ] T014 Add audio and video response builders in Python
- [ ] T015 Add Node handling for media references and delivery acknowledgements

## Phase 5: Hardening and Validation

**Goal**: Close the contract gaps and prove the end-to-end flow locally.

- [ ] T016 Add contract tests for the Node -> Python API
- [ ] T017 Add integration tests for the happy path and fallback path
- [ ] T018 Add retry handling and structured logging for both services
- [ ] T019 Update quickstart notes with the dual-service run instructions

## Execution Order

1. Freeze the contract first.
2. Build the Node relay next.
3. Move the Python processing API behind the contract.
4. Add audio and video media delivery.
5. Finish with tests and smoke validation.