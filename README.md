# Alfabot Marajoara

**Alfabot Marajoara** é um backend em Python projetado para atuar como um **tutor de alfabetização inteligente via WhatsApp**. O projeto combina **IA generativa local** com **RAG (Retrieval-Augmented Generation)** enriquecido por conteúdos da cultura marajoara, oferecendo suporte pedagógico personalizado, inclusivo e culturalmente relevante para crianças e adultos em processo de alfabetização.

---

##  Funcionalidades Implementadas

- **Webhooks Assíncronos**: Processamento de mensagens via WhatsApp Cloud API com respostas imediatas (evita timeouts do Meta). Processamento pesado é feito em segundo plano com *threading*.
- **Pipeline de IA Local**:
  - **Transcrição de áudio**: Conversão de mensagens de voz do WhatsApp para texto usando **Faster-Whisper** (otimizado para CPU).
  - **Geração de Respostas**: Respostas pedagógicas contextuais geradas por **Llama 3.2** via **Ollama**.
- **Memória Cultural (RAG)**: Busca semântica com **ChromaDB** para recuperar informações sobre fauna, lendas, história e tradições marajoaras, tornando o aprendizado mais significativo.
- **Gestão de Aprendizado**: Banco de dados SQLite com **SQLAlchemy** para gerenciar perfis de alunos, níveis de leitura (Iniciante, Básico, Intermediário) e histórico de interações.

---

##  Tecnologias Utilizadas

- **Backend**: Python 3, Flask, Gunicorn
- **IA/ML**: Ollama (Llama 3.2), Faster-Whisper, ChromaDB
- **Banco de Dados**: SQLite + SQLAlchemy (relacional) e ChromaDB (vetorial)
- **Observabilidade**: Loguru
- **Gestão de Dependências**: `uv`
- **Outros**: Python-dotenv, Requests

---

##  Estrutura do Projeto

```text
alfabot-marajoara/
├── app/
│   ├── models/          # Modelos SQLAlchemy
│   ├── services/        # Lógica de IA, RAG, Voz e WhatsApp
│   ├── routes/          # Webhooks Flask
│   └── database.py      # Configuração do banco
├── data/                # Áudios temporários e artefatos
├── deploy/              # Configurações de produção (Systemd, Gunicorn)
├── tests/               # Testes com Pytest
├── .env.example
├── main.py              # Ponto de entrada
└── pyproject.toml       # Dependências com uv
```

---

##  Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/DanielRond/AlfabetizacaoIA.git
cd AlfabetizacaoIA
```

### 2. Instale as dependências

```bash
# Cria o ambiente virtual
uv venv

# Ativa o ambiente (Linux/Mac)
source .venv/bin/activate

# Instala as dependências
uv pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais:

```env
# API WhatsApp
WHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_VERIFY_TOKEN=seu_token_verificacao

# IA (escolha entre gemini ou ollama)
IA_PROVIDER=ollama
OLLAMA_MODEL=llama3.2

# Opcional: Gemini
# IA_PROVIDER=gemini
# GEMINI_API_KEY=sua_chave

LOG_LEVEL=INFO
```

### 4. Inicie os serviços de IA

```bash
# Inicie o Ollama (se estiver usando)
ollama serve
ollama pull llama3.2
```

### 5. Execute a aplicação

```bash
uv run python main.py
```

Ou diretamente:

```bash
python -m src.alfabot.main
```

### 6. Expor o webhook (desenvolvimento)

Use o **Hookdeck** ou **ngrok**:

```bash
hookdeck listen 5000
```

---

## 🚀 Deploy em Produção

Consulte a pasta `deploy/` para configurações de **Gunicorn** + **Systemd**.

---

## 📝 Licença

Este projeto é desenvolvido para fins **educacionais e de pesquisa**. Sinta-se à vontade para estudar, contribuir e adaptar.

---

**Desenvolvido por [DanielRond](https://github.com/DanielRond)**

🌐 [Repositório no GitHub](https://github.com/DanielRond/AlfabetizacaoIA/)

---

**Alfabot Marajoara** — Alfabetizando com inteligência e raiz marajoara. 🇧🇷
```

