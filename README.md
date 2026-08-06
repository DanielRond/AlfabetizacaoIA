# Curumim Marajoara

**Curumim Marajoara** é o backend em Python de um **tutor de alfabetização inteligente via WhatsApp**. O projeto combina **IA generativa** (Ollama ou Gemini) com **RAG (Retrieval-Augmented Generation)** enriquecido por conteúdos da cultura marajoara, oferecendo suporte pedagógico personalizado, inclusivo e culturalmente relevante para crianças e adultos em processo de alfabetização.

O backend expõe uma API interna que recebe mensagens normalizadas de um conector WhatsApp (Node.js) e retorna instruções estruturadas (texto, áudio ou pedido de repetição). O contrato entre os serviços está documentado em [`specs/002-whatsappjs-python-split/contracts/node-python-api.md`](specs/002-whatsappjs-python-split/contracts/node-python-api.md).

---

## Funcionalidades

* **API interna (Flask)**: endpoints `/health` e `/v1/messages/inbound` que processam mensagens, gerenciam perfil e histórico do aluno e retornam um `ProcessingResult` estruturado.
* **Onboarding pedagógico**: identifica o nível do aluno (iniciante, básico ou intermediário) antes de iniciar o atendimento.
* **Memória Cultural (RAG)**: busca semântica com **ChromaDB** sobre fauna, lendas, história e tradições marajoaras.
* **Transcrição de áudio (STT)**: mensagens de voz convertidas em texto com **NVIDIA NeMo Parakeet**.
* **Geração de respostas (IA)**: respostas pedagógicas contextuais via **Ollama (Llama 3.2)** ou **Google Gemini**.
* **Resposta em áudio (TTS)**: síntese de voz local com **Kokoro** (CPU), com reforço de áudio para alunos iniciantes.
* **Gestão de aprendizado**: SQLite + **SQLAlchemy** para perfis de alunos, níveis de leitura e histórico de interações.

---

## Estrutura do Projeto

```text
AlfabetizacaoIA/
├── src/curumim/
│   ├── main.py                 # Aplicação Flask e rotas da API
│   ├── logger_config.py        # Configuração do Loguru (console + arquivo)
│   ├── models/
│   │   └── database.py         # SQLAlchemy: models e engine SQLite
│   └── services/
│       ├── ai_service.py       # Orquestração de IA (Ollama/Gemini)
│       ├── rag_service.py      # ChromaDB (busca e ingestão de contexto)
│       ├── stt_service.py      # Transcrição de áudio (NeMo Parakeet)
│       └── tts_service.py      # Síntese de voz (Kokoro)
├── scripts/
│   └── ingest_knowledge.py     # Utilidade: popula o ChromaDB com data/knowledge
├── tests/                      # Testes pytest (unitários e integração)
├── data/
│   └── knowledge/              # Textos marajoaras para o RAG
├── deploy/
│   └── gunicorn_config.py      # Configuração de produção (Gunicorn)
├── .env.example
├── pyproject.toml              # Dependências e config (uv)
└── uv.lock
```

---

## Como Executar

### 1. Pré-requisitos

* Python 3.11+ e [uv](https://docs.astral.sh/uv/)
* [Ollama](https://ollama.com/) instalado (se usar geração local)
* (Opcional) Chave da API do Google Gemini

### 2. Instale as dependências

```bash
# Cria o ambiente virtual e instala tudo (incluindo dependências de dev/teste)
uv sync
```

### 3. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` conforme necessário:

```env
# Servidor
PORT=5000
LOG_LEVEL=INFO

# IA (escolha entre 'ollama' ou 'gemini')
IA_PROVIDER=ollama
OLLAMA_API_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3.2

# Opcional: Gemini
# IA_PROVIDER=gemini
# GEMINI_API_KEY=sua_chave
# GEMINI_MODEL=gemini-flash-latest

# TTS (Kokoro)
TTS_ENABLED=true
TTS_VOICE=pf_dora
KOKORO_MODEL_PATH=models/kokoro-v1.0.onnx
KOKORO_VOICES_PATH=models/voices-v1.0.bin
```

### 4. (Opcional) Popule o RAG com conteúdos marajoaras

```bash
uv run python scripts/ingest_knowledge.py
```

Os arquivos `.txt` em `data/knowledge/` são indexados no ChromaDB.

### 5. Inicie os serviços de IA

```bash
# Inicie o Ollama (se estiver usando)
ollama serve
ollama pull llama3.2
```

### 6. Execute a aplicação

```bash
uv run python -m curumim.main
```

O backend sobe em `http://localhost:5000` (porta configurável via `PORT`). Verifique com:

```bash
curl http://localhost:5000/health
```

---

## Testes

```bash
# Testes unitários (não exigem serviços externos)
uv run pytest

# Testes de integração (exigem Ollama/Gemini, modelos TTS e ChromaDB populado)
uv run pytest -m integration
```

---

## Deploy em Produção

O projeto usa **Gunicorn** em produção, com a configuração em `deploy/gunicorn_config.py`:

```bash
uv run gunicorn -c deploy/gunicorn_config.py "curumim.main:create_app()"
```

---

## Tecnologias Utilizadas

* **Backend**: Python 3, Flask, Gunicorn
* **IA/ML**: Ollama (Llama 3.2) ou Google Gemini, NVIDIA NeMo Parakeet (STT), Kokoro (TTS), ChromaDB
* **Banco de Dados**: SQLite + SQLAlchemy (relacional) e ChromaDB (vetorial)
* **Observabilidade**: Loguru
* **Gestão de Dependências**: `uv`
* **Outros**: Python-dotenv, Requests

---

## Desenvolvedores

* **Daniel Rond** — [GitHub](https://github.com/DanielRond)
* **Vinicius Melo** — [GitHub](https://github.com/Vinicius-MCS)
* **João Arruda** — [GitHub](https://github.com/Jparruda)

---

## Licença

Este projeto é desenvolvido para fins **educacionais e de pesquisa**. Sinta-se à vontade para estudar, contribuir e adaptar.

---

**Curumim Marajoara** — Alfabetizando com inteligência e raiz marajoara.
