# 01 — Visão Geral

## Propósito

**Curumim Marajoara** é um tutor de alfabetização inteligente via WhatsApp. O
objetivo é oferecer suporte pedagógico personalizado, inclusivo e culturalmente
relevante para crianças e adultos em processo de alfabetização, usando conteúdo da
cultura marajoara (fauna, lendas, história e tradições) como material de ensino.

O projeto combina:

- **IA generativa** (Ollama local ou Google Gemini) para gerar respostas pedagógicas;
- **RAG** (ChromaDB) para enriquecer as respostas com conhecimento marajoara;
- **STT** (NVIDIA NeMo Parakeet) para transcrever mensagens de voz;
- **TTS** (Kokoro, local em CPU) para responder em áudio, com reforço para iniciantes.

## Funcionalidades

| Funcionalidade | Descrição | Onde |
|---|---|---|
| API interna Flask | Endpoints `/health`, `/v1/messages/inbound` e `/v1/messages/delivered` | `src/curumim/main.py` |
| Onboarding pedagógico | Identifica o nível do aluno (iniciante, básico ou intermediário) antes do atendimento | `src/curumim/main.py:_processar_negocio_ia` |
| Memória Cultural (RAG) | Busca semântica no ChromaDB sobre conteúdos marajoaras | `src/curumim/services/rag_service.py` |
| Transcrição de áudio (STT) | Mensagens de voz viram texto via NVIDIA Parakeet (lazy-load) | `src/curumim/services/stt_service.py` |
| Geração de respostas (IA) | Respostas contextuais via Ollama (Llama 3.2) ou Gemini | `src/curumim/services/ai_service.py` |
| Resposta em áudio (TTS) | Síntese de voz local com Kokoro; reforço de áudio para iniciantes | `src/curumim/services/tts_service.py` |
| Conector WhatsApp (Node) | Sessão via whatsapp-web.js (QR login), normalização, envio e ack | `apps/whatsapp-connector/src/` |
| Gestão de aprendizado | SQLite + SQLAlchemy: perfis, níveis, histórico e rastreio | `src/curumim/models/database.py` |

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11+, Flask, Gunicorn |
| Conector | Node.js 18+, whatsapp-web.js, Pino, dotenv |
| IA/ML | Ollama (Llama 3.2), Google Gemini, NVIDIA NeMo Parakeet (STT), Kokoro (TTS) |
| Armazenamento | SQLite + SQLAlchemy (relacional), ChromaDB (vetorial), filesystem (mídia) |
| Observabilidade | Loguru (Python), Pino (Node), rastreio por `correlation_id` |
| Dependências | uv (Python), npm (Node) |

## Estrutura do repositório

```text
AlfabetizacaoIA/
├── AGENTS.md                        # Guia para agentes de IA
├── apps/
│   └── whatsapp-connector/          # Serviço Node: transporte WhatsApp
│       ├── src/                     # index, config, logger, session, handlers,
│       │                            # normalizer, media, apiClient, sender
│       └── tests/                   # Testes node:test (42)
├── docs/                            # Esta documentação
├── src/curumim/                     # Serviço Python: processamento e IA
│   ├── main.py                      # Flask, rotas e lógica de onboarding
│   ├── logger_config.py             # Loguru (console + arquivo rotativo)
│   ├── models/database.py           # SQLAlchemy models e engine SQLite
│   └── services/                    # ai_service, rag_service, stt_service, tts_service
├── scripts/ingest_knowledge.py      # Popula o ChromaDB com data/knowledge
├── tests/                           # Testes pytest (45 unit + 4 integração)
├── deploy/gunicorn_config.py        # Config de produção
├── specs/002-whatsappjs-python-split/  # Spec, plan, research, data-model, contracts
├── data/                            # knowledge/, audios/ (TTS), chroma_db/, media_in/
├── models/                          # Kokoro .onnx e voices (não versionado)
├── .env.example
├── pyproject.toml                   # Deps Python e config pytest (uv)
└── uv.lock
```

## Pontos de atenção para quem desenvolve

- **Dois runtimes**: Node fala com WhatsApp; Python processa. O Node **não** conhece
  regras pedagógicas e o Python **não** fala com a Meta.
- **Contrato versionado**: toda troca entre os serviços passa pelo contrato em
  [`specs/002-whatsappjs-python-split/contracts/node-python-api.md`](../specs/002-whatsappjs-python-split/contracts/node-python-api.md).
- **Rastreio ponta a ponta**: o `correlation_id` gerado no Node conecta payload,
  logs (Pino/Loguru) e `InteractionRecord`.
- **Modelos pesados** (Parakeet, Kokoro) são carregados com *lazy-load* e lock para
  não pagar o custo de carga no startup.

## Próximos documentos

- [02-arquitetura.md](02-arquitetura.md) — como os serviços se dividem e conversam.
- [03-fluxos.md](03-fluxos.md) — o caminho de uma mensagem ponta a ponta.
