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
├── apps/
│   └── whatsapp-connector/      # Conector WhatsApp em Node.js (whatsapp-web.js)
│       ├── src/                 # Sessão, normalização, envio e relay para a API
│       └── tests/               # Testes node:test
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

## Quick Start

Dois caminhos para rodar o projeto — escolha o seu:

| Caminho | Para quem | Comandos |
|---|---|---|
| **A — Dev (sem Docker)** | Desenvolver/testar rápido | ~6 comandos (abaixo) |
| **B — Deploy (Docker Compose)** | Subir o sistema completo em produção | ~5 comandos (abaixo) |

### Caminho A — Dev (sem Docker)

```bash
uv sync                                     # instala dependências Python
cp .env.example .env                        # configure IA e TTS
uv run python scripts/ingest_knowledge.py   # (opcional) popula o RAG
ollama serve                                # terminal 1 (opcional): daemon da IA local
ollama pull llama3.2                        # depois de iniciado (uma vez)
uv run python -m curumim.main               # terminal 2: backend (http://localhost:5000)

# terminal 3: conector WhatsApp (QR na 1ª execução)
cd apps/whatsapp-connector && npm install && npm start
```

Detalhes: [Como Executar](#como-executar) e [Rodar com o Conector WhatsApp (Node)](#rodar-com-o-conector-whatsapp-node).

### Caminho B — Deploy (Docker Compose)

```bash
cd deploy
cp .env.compose.example .env                # configure IA, TTS e chaves
make build                                  # constrói as imagens (baixa modelos Kokoro)
make up                                     # sobe backend + connector
make qr                                     # 1ª vez: escaneie o QR do WhatsApp
```

IA local opcional (Ollama):

```bash
make up-ollama                              # sobe o container do Ollama
docker exec curumim-ollama ollama pull llama3.2   # baixa o modelo (uma vez)
```

> **IA**: sem o Ollama, defina `IA_PROVIDER=gemini` (e `GEMINI_API_KEY`) no `deploy/.env`,
> senão o backend responde com o fallback de "estou com dificuldades".

> **Voz do TTS**: as 3 vozes PT-BR (`pm_santa`, `pf_dora`, `pm_alex`) já vêm no
> `voices-v1.0.bin` da imagem. Trocar de voz = editar `TTS_VOICE` no `deploy/.env`
> (exemplo usa `pm_santa`; o default do código é `pf_dora`) — **sem rebuild**.

Detalhes (volumes, troubleshooting, systemd): [docs/09-operacao.md](docs/09-operacao.md).

---

## Como Executar

### 1. Pré-requisitos

* Python 3.11+ e [uv](https://docs.astral.sh/uv/)
* [Ollama](https://ollama.com/) instalado (se usar geração local)
* Node.js 18+ (para o conector WhatsApp)
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

## Rodar com o Conector WhatsApp (Node)

A arquitetura separa o transporte WhatsApp (Node) do processamento de IA (Python). O conector mantém a sessão, normaliza mensagens e as repassa ao backend via `POST /v1/messages/inbound` (contrato em `specs/002-whatsappjs-python-split/contracts/node-python-api.md`).

### 1. Instale as dependências do conector

```bash
cd apps/whatsapp-connector
npm install
```

### 2. Configure o ambiente do conector

```bash
cp .env.example .env
```

O conector lê primeiro `apps/whatsapp-connector/.env` e depois o `.env` da raiz do repositório.

### 3. Inicie os dois serviços (em terminais separados)

```bash
# Terminal 1 - backend Python (veja a seção "Como Executar")
uv run python -m curumim.main

# Terminal 2 - conector WhatsApp
cd apps/whatsapp-connector
npm run start
```

Na primeira execução, um **QR code** aparece no terminal. Escaneie com o WhatsApp Web do telefone vinculado. Nas próximas execuções a sessão é restaurada automaticamente (`LocalAuth`).

### 4. Testes do conector

```bash
cd apps/whatsapp-connector
npm test
```

> **Observação**: ao rodar `npm install`, o download do Chromium pode ser pulado com `PUPPETEER_SKIP_DOWNLOAD=true`. Nesse caso, o conector usa o Chrome instalado na máquina via `puppeteer-core`.

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

O caminho oficial é **Docker Compose** (`deploy/compose.yaml` + `deploy/Makefile`):
veja o passo a passo no [Quick Start](#quick-start) e os detalhes em
[docs/09-operacao.md](docs/09-operacao.md).

Alternativa sem container (Gunicorn):

```bash
uv run gunicorn -c deploy/gunicorn_config.py "curumim.main:create_app()"
```

---

## Tecnologias Utilizadas

* **Backend**: Python 3, Flask, Gunicorn
* **Conector WhatsApp**: Node.js, whatsapp-web.js, Pino, dotenv
* **IA/ML**: Ollama (Llama 3.2) ou Google Gemini, NVIDIA NeMo Parakeet (STT), Kokoro (TTS), ChromaDB
* **Banco de Dados**: SQLite + SQLAlchemy (relacional) e ChromaDB (vetorial)
* **Observabilidade**: Loguru (Python) e Pino (Node)
* **Gestão de Dependências**: `uv` (Python) e `npm` (Node)
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
