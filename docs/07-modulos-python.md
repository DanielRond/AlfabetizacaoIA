# 07 — Módulos do Backend Python

Código em `src/curumim/`. Pacote instalável via `pyproject.toml` (src layout, `uv`).

```text
src/curumim/
├── __init__.py
├── main.py                  # App Flask, rotas e lógica de negócio
├── logger_config.py         # Loguru (console + arquivo rotativo)
├── models/
│   ├── __init__.py
│   └── database.py          # SQLAlchemy models, engine e migração
└── services/
    ├── __init__.py
    ├── ai_service.py        # RAG + geração (Ollama/Gemini)
    ├── rag_service.py       # ChromaDB (busca e ingestão)
    ├── stt_service.py       # Transcrição (NVIDIA Parakeet, lazy-load)
    └── tts_service.py       # Síntese de voz (Kokoro) + limpeza
```

## `logger_config.py` — Loguru

- Remove handlers padrão para evitar duplicidade.
- Console: cor, formato `{time} | {level} | {name}:{function} - {message}`, nível via
  `LOG_LEVEL` (default `INFO`).
- Arquivo: `logs/alfabot_{data}.log`, rotação à meia-noite, retenção 10 dias,
  compressão zip.

## `models/database.py` — Banco de dados

- Define `PROJECT_ROOT = Path(__file__).resolve().parents[2]` → **`src/`**, então o
  banco fica em `src/data/curumim.db`.
- Modelos: `LearnerProfile`, `ChatMessage`, `MediaArtifact`, `InteractionRecord`
  (detalhes em [05-banco-de-dados.md](05-banco-de-dados.md)).
- `inicializar_banco()`: `create_all` + `_adicionar_coluna_se_faltar` idempotente
  para `display_name` e `last_seen_at`.
- `SessionLocal` = sessionmaker vinculado ao engine (check_same_thread=False).

## `main.py` — Aplicação e orquestração

### `create_app()` — fábrica do Flask

- Roda `inicializar_banco()` no app context.
- Registra rotas:
  - `POST /v1/messages/inbound` → `handle_inbound_message`;
  - `POST /v1/messages/delivered` → `handle_message_delivered`;
  - `GET /health` e `GET /v1/health` → `health_check`.

### `handle_inbound_message` — endpoint principal

1. Valida JSON (`INVALID_JSON_PAYLOAD`) e campos obrigatórios `phone_number` /
   `correlation_id` (`MISSING_REQUIRED_FIELDS`).
2. **Áudio** (`message_type == 'audio'`): transcreve via `transcrever_audio(media_ref)`.
   - Falha → `request_retry` / `AUDIO_TRANSCRIPTION_FAILED`; arquivo ausente →
     `MEDIA_FILE_NOT_FOUND`.
3. **Imagem**: responde recusa amigável (`send_text`) e salva via `_salvar_interacao_banco`.
4. Texto vazio → `noop`.
5. `_processar_negocio_ia(phone_number, texto, veio_como_audio)` → resposta + nível + flag onboarding.
6. Se `not em_onboarding and tts_disponivel() and deve_incluir_audio(nível, veio_como_audio)`:
   - `sintetizar_fala(resposta)` → se ok, `action = "send_audio"` e `_registrar_artefato_audio`.
7. `_registrar_interacao(...)` (InteractionRecord inbound).
8. Retorna o envelope `ProcessingResult`.

Exceções gerais → `error` / `INTERNAL_SERVER_ERROR` (500).

### `handle_message_delivered` — ack de entrega

1. Valida `correlation_id` e `status ∈ {delivered, failed}`; senão `400`.
2. Localiza o perfil: primeiro pelo `InteractionRecord` do `correlation_id`, depois
   por `phone_number`. Sem perfil → `200 {"status": "ok"}` (no-op).
3. Grava `InteractionRecord` **outbound** (`sent`/`failed`) com o payload em
   `payload_snapshot`.
4. Se `action == "send_audio"` e `media_ref`: marca o `MediaArtifact` (`sent`/`failed`).
5. Retorna `200 {"status": "ok"}` (idempotente; erros são logados, não estouram).

### Regras de negócio auxiliares

- `_processar_negocio_ia(numero, texto, veio_como_audio)`: busca/cria o perfil,
  atualiza `last_seen_at`, salva `ChatMessage` do usuário, executa a máquina de
  onboarding (ver `03-fluxos.md`), chama `gerar_resposta_ia` quando `active` e salva
  a `ChatMessage` do assistente.
- `_interpretar_nivel(texto)`: normaliza acentos e mapeia "intermediario/avancado/
  medio", "basico", "iniciante/iniciando/novo".
- `deve_incluir_audio(nivel, veio_como_audio)`:
  - `new`/`iniciante` → sempre áudio;
  - `basico` → áudio se o aluno mandou áudio;
  - `intermediario` → só texto.
- `_salvar_interacao_banco`, `_registrar_interacao`, `_registrar_artefato_audio`:
  persistência com try/except (falha de persistência não derruba a resposta).

## `services/ai_service.py` — IA

- Configurações globais lidas uma vez: `IA_PROVIDER` (`ollama` default), `OLLAMA_URL`,
  `OLLAMA_MODEL` (`llama3.2`), `GEMINI_MODEL`.
- `_get_gemini_client()`: cliente `google.genai` **lazy** (importa e cria só quando
  `PROVIDER == "gemini"`); levanta `ValueError` sem `GEMINI_API_KEY`.
- `_gerar_com_ollama(prompt)`: `requests.post` para `/api/generate` (stream=False,
  timeout 120 s); extrai `response` com `str()` seguro.
- `_gerar_com_gemini(prompt)`: `client.models.generate_content`.
- `gerar_resposta_ia(mensagem, nivel)`: busca contexto no RAG, monta o prompt
  pedagógico com o CONTEXTO, escolhe o provedor e captura exceções com fallback
  (*"Desculpe, estou com dificuldades para pensar agora..."*).

## `services/rag_service.py` — ChromaDB

- Coleção `conhecimento_marajo`, persistência em `data/chroma_db`.
- `_get_collection()`: inicialização lazy (`PersistentClient` +
  `get_or_create_collection`), protegida por `_collection is None`.
- `adicionar_conhecimento(texto, id_documento)`: adiciona documento (usado pelo
  script de ingestão).
- `buscar_contexto(pergunta, n_resultados=2)`: query semântica; extrai documentos de
  forma segura (trata lista-de-listas e ausência de chaves) e retorna texto unido
  por `\n`. Falha → `""`.

## `services/stt_service.py` — Transcrição (NVIDIA Parakeet)

- Modelo `nvidia/parakeet-tdt-0.6b-v3` carregado **lazy** com `threading.Lock`.
- `transcrever_audio(caminho)`: valida existência do arquivo, `modelo.transcribe`
  dentro de `torch.inference_mode()`, extrai o texto da primeira resposta
  (desembrulhando lista/tupla) e limpa. Erros são relançados (o `main.py` os
  transforma em `request_retry`).
- Dispositivo: CUDA se disponível, senão CPU.

## `services/tts_service.py` — Síntese de voz (Kokoro)

- Config: `TTS_ENABLED`, `TTS_VOICE` (`pf_dora`), caminhos dos modelos Kokoro,
  `MEDIA_RETENTION_HOURS` (default 24).
- `_limpar_texto_para_audio(texto)`: remove Markdown (**bold**, *itálico*, headers,
  itens de lista), emojis, espaços antes de pontuação e espaços múltiplos; garante
  que cada linha termina com pontuação — leitura natural pelo Kokoro.
- `_carregar_kokoro()`: lazy + lock; valida a existência dos modelos em `models/`;
  usa `espeak` (caminhos hard-coded Linux).
- `tts_disponivel()`: `TTS_ENABLED` e modelos presentes.
- `limpar_artefatos_antigos(pasta, max_idade_horas)`: remove arquivos com `mtime`
  mais antigo que o limite (default `MEDIA_RETENTION_HOURS`); retorna contagem.
- `sintetizar_fala(texto)`: limpa o texto, gera `.wav` via Kokoro, converte para
  `.ogg` (Opus 32k, 24 kHz mono) com **ffmpeg**, remove o `.wav` temporário e
  retorna o caminho `.ogg`. Falha → `None`. Chama `limpar_artefatos_antigos()` no início.

## `scripts/ingest_knowledge.py` — População do RAG

- Lê `data/knowledge/*.txt` e chama `rag_service.adicionar_conhecimento` com o nome
  do arquivo como id.

## Testes (45 unit + 4 integração, pytest)

- `tests/test_main.py` — endpoints, onboarding, áudio/imagem, retry, rastreio,
  delivered (400/no-profile), migração idempotente.
- `tests/services/test_ai_service.py`, `test_rag_service.py`, `test_stt_service.py`,
  `test_tts_service.py` — unitários com mocks/patch.
- `tests/contract/test_contrato.py` — valida o backend contra as fixtures do contrato.
- `tests/integration/test_fluxos_reais.py` — `-m integration`: TTS/RAG/IA reais
  (skippam quando modelos/provedores indisponíveis).

## Próximos documentos

- [06-modulos-node.md](06-modulos-node.md) — o conector que consome esta API.
- [09-operacao.md](09-operacao.md) — como rodar e testar.
