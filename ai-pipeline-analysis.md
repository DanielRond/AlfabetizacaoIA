# Análise do Pipeline de IA — AlfaBot Marajoara

**Data da análise**: 2026-06-10  
**Branch analisado**: master  
**Escopo**: Fluxo completo de processamento de mensagens, desempenho de IA, modelo de linguagem e RAG

---

## 1. Visão Geral do Fluxo Atual

```
WhatsApp User
    │
    ▼ POST /webhook (Meta Cloud API)
Flask — main.py (SÍNCRONO ⚠️)
    │
    ├─ Texto: extrai body
    └─ Áudio: baixa (Meta API) → transcreve (Faster-Whisper)
    │
    ▼
SQLite — busca/cria LearnerProfile
    │
    ▼
ai_service.gerar_resposta_ia()
    ├─ RAG: ChromaDB.query() → top-2 documentos
    ├─ Monta prompt (sem instrução de língua)
    └─ Ollama HTTP POST (stream=False, timeout=120s)
         modelo: llama3.2 (3B, sem parâmetros de geração)
    │
    ▼
whatsapp_service.enviar_mensagem_texto()
    └─ POST Meta API (timeout=10s)
    │
    ▼
Retorna 200 à Meta (APÓS tudo ⚠️)
```

**Tempo total estimado** (hardware CPU, <8GB RAM):
| Etapa | Tempo estimado |
|-------|---------------|
| Download de áudio (se aplicável) | 0.5–2s |
| Transcrição Whisper `base` | 1–3s |
| Query ChromaDB | <0.1s |
| Inferência Ollama llama3.2 | 4–12s |
| Envio WhatsApp API | 0.5–1s |
| **Total (áudio)** | **6–18s** |
| **Total (texto)** | **5–13s** |

---

## 2. Problemas Identificados

### 2.1 Processamento Síncrono no Webhook (CRÍTICO)

**Arquivo**: `src/alfabot/main.py` — `receber_mensagem()` (linha 46–55)

```python
def receber_mensagem():
    dados = request.json
    for msg_info in _extrair_mensagens(dados):
        processar_mensagem_whatsapp(msg_info)  # ← bloqueia aqui
    return jsonify({"status": "recebido"}), 200  # ← Meta só recebe 200 depois
```

**Problema**: A Meta exige resposta 200 em até ~15-20 segundos. Se o processamento ultrapassar esse tempo (comum com áudio + LLM em CPU), a Meta **reenvia o webhook**, causando mensagens duplicadas enviadas ao aluno.

**Impacto**: Alto — causa bugs visíveis ao usuário (mensagem duplicada ou triplicada).

---

### 2.2 Timeout Excessivo no Ollama (ALTO)

**Arquivo**: `src/alfabot/services/ai_service.py` — linha 31

```python
response = requests.post(OLLAMA_URL, json=payload, timeout=120)
```

**Problema**: 120 segundos é tempo para o usuário desistir da conversa. Não há tratamento de SLA — se o Ollama travar, o Flask fica bloqueado por 2 minutos.

**Impacto**: Alto — degrada experiência de usuário e bloqueia threads do servidor.

---

### 2.3 Ausência de Parâmetros de Geração no Ollama (ALTO)

**Arquivo**: `src/alfabot/services/ai_service.py` — linha 30

```python
payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
# Sem: num_predict, temperature, num_ctx
```

**Problemas**:
- Sem `num_predict`: o modelo pode gerar respostas muito longas (500+ palavras), inadequado para WhatsApp e lento em CPU
- Sem `temperature`: comportamento imprevisível (o default varia por modelo e versão)
- Sem `num_ctx`: janela de contexto usa o default do modelo (pode ser 4096+), consumindo mais RAM e aumentando latência

**Impacto**: Alto — respostas longas, latência aumentada, inconsistência entre modelos.

---

### 2.4 Prompt Sem Instrução de Língua (MÉDIO)

**Arquivo**: `src/alfabot/services/ai_service.py` — linhas 57–66

```python
prompt = f"""Você é um professor amigável e paciente, ensinando um aluno de nível {nivel_pedagogico}.
Use o CONTEXTO abaixo para responder à pergunta do aluno...
CONTEXTO: {contexto}
PERGUNTA: {mensagem_usuario}
RESPOSTA:"""
```

**Problemas**:
- Modelos multilíngues (especialmente `qwen2.5`) podem responder em inglês se o input estiver em outro idioma
- Nenhuma instrução de tamanho de resposta — sem limite explícito de parágrafos
- Sem instrução de formatação para WhatsApp (sem markdown complexo, sem listas muito longas)

**Impacto**: Médio — afeta qualidade e adequação das respostas.

---

### 2.5 RAG com Poucos Resultados e Embeddings em Inglês (MÉDIO)

**Arquivo**: `src/alfabot/services/rag_service.py` — linha 44

```python
def buscar_contexto(pergunta: str, n_resultados: int = 2) -> str:
```

**Problemas**:
- `n_results=2` pode ser insuficiente conforme a base de conhecimento cresce
- O ChromaDB usa por padrão o modelo `all-MiniLM-L6-v2` (inglês) para embeddings — reduz a qualidade da busca semântica em português
- Sem score threshold: documentos pouco relevantes são incluídos no contexto

**Impacto**: Médio — contexto incompleto ou irrelevante degrada qualidade das respostas.

---

### 2.6 Whisper Hardcoded (BAIXO)

**Arquivo**: `src/alfabot/services/voice_service.py` — linha 12

```python
model = WhisperModel("base", device="cpu", compute_type="int8")
```

**Problema**: Modelo e device são literais, não configuráveis por variável de ambiente. Para trocar o modelo, é necessário editar o código.

**Impacto**: Baixo — dificulta tuning e ajuste por ambiente.

---

## 3. Análise de Modelos Open-Source

### Contexto de Hardware
O projeto roda em CPU com menos de 8GB de RAM disponível. Modelos acima de 4-5B parâmetros são inviáveis (latência >20s e risco de OOM).

### Comparativo (modelos viáveis para CPU <8GB)

| Modelo | RAM Ollama | Qualidade PT | Velocidade CPU | Indicado para PT educacional |
|--------|-----------|--------------|---------------|------------------------------|
| `llama3.2:3b` *(atual)* | ~2.2 GB | Razoável | 4–8s/resp | Sim, mas limitado |
| `qwen2.5:3b` | ~2.2 GB | **Boa** | 5–9s/resp | **✅ Recomendado** |
| `phi3.5:mini` (3.8B) | ~2.8 GB | Boa | 6–10s/resp | Alternativa viável |
| `llama3.2:1b` | ~1.1 GB | Fraca | 1–3s/resp | Apenas se RAM for crítica |
| `mistral:7b` | ~5.0 GB | Excelente | 15–30s/resp | ❌ Lento demais para este HW |
| `llama3.1:8b` | ~6.0 GB | Muito boa | 20–35s/resp | ❌ Risco de OOM |

### Recomendação: `qwen2.5:3b`

**Motivos**:
- Treinado em 18+ idiomas com foco em multilíngue — **melhor suporte ao português** entre os modelos 3B
- Mesmo footprint de memória que o `llama3.2:3b` atual
- Drop-in replacement: apenas mudar `OLLAMA_MODEL=qwen2.5:3b` no `.env` e executar `ollama pull qwen2.5:3b`
- Benchmarks mostram superioridade em compreensão e geração em PT vs. Llama 3.2 3B

**Caminho de upgrade futuro** (se hardware melhorar):
- GPU disponível → `qwen2.5:7b` ou `mistral:7b`
- 16GB+ RAM → `llama3.1:8b`

---

## 4. Plano de Implementação

### Prioridade 1 — Crítico (segurança e confiabilidade)

#### 4.1 Webhook Assíncrono — `src/alfabot/main.py`

Adicionar `import threading` e modificar `receber_mensagem()`:

```python
import threading

def receber_mensagem() -> Tuple[Response, int]:
    dados = request.json
    if not dados or 'entry' not in dados:
        return jsonify({"status": "recebido"}), 200

    for msg_info in _extrair_mensagens(dados):
        thread = threading.Thread(
            target=processar_mensagem_whatsapp,
            args=(msg_info,),
            daemon=True
        )
        thread.start()

    return jsonify({"status": "recebido"}), 200
```

**Nenhuma outra função precisa mudar.** `daemon=True` garante que threads não bloqueiem o shutdown do servidor.

---

### Prioridade 2 — Alto (desempenho e qualidade)

#### 4.2 Parâmetros de Geração + Timeout + Prompt — `src/alfabot/services/ai_service.py`

**a) Adicionar constantes de configuração** (após as linhas de `GEMINI_MODEL`):

```python
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "45"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "250"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "1024"))
```

**b) Atualizar `_gerar_com_ollama()`** — substituir payload e timeout:

```python
def _gerar_com_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": OLLAMA_NUM_PREDICT,
            "temperature": OLLAMA_TEMPERATURE,
            "num_ctx": OLLAMA_NUM_CTX,
        }
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
    response.raise_for_status()
    conteudo = response.json().get("response")
    return str(conteudo).strip() if conteudo else ""
```

**c) Melhorar o template de prompt** em `gerar_resposta_ia()`:

```python
prompt = f"""Você é um professor amigável e paciente ensinando alfabetização para um aluno de nível {nivel_pedagogico}. Responda SEMPRE em português do Brasil. Seja breve (no máximo 3 parágrafos curtos, sem formatação markdown).
Use o CONTEXTO abaixo para responder. Se a resposta não estiver no contexto, diga honestamente que não sabe, mas tente ajudar de forma educativa.

CONTEXTO:
{contexto}

PERGUNTA:
{mensagem_usuario}

RESPOSTA:"""
```

---

#### 4.3 Aumentar n_results no RAG — `src/alfabot/services/rag_service.py`

Alterar apenas a assinatura da função (linha 44):

```python
# Antes:
def buscar_contexto(pergunta: str, n_resultados: int = 2) -> str:

# Depois:
def buscar_contexto(pergunta: str, n_resultados: int = 3) -> str:
```

---

### Prioridade 3 — Médio (configurabilidade)

#### 4.4 Whisper Configurável — `src/alfabot/services/voice_service.py`

Substituir as linhas de carregamento do modelo:

```python
# Antes:
model = WhisperModel("base", device="cpu", compute_type="int8")

# Depois:
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type="int8")
```

Adicionar `import os` no topo se não existir (já existe no arquivo atual).

---

#### 4.5 Atualizar `.env.example`

Adicionar/atualizar as seguintes variáveis com comentários:

```env
# === OLLAMA (Inteligência Artificial Local) ===
OLLAMA_API_URL=http://localhost:11434/api/generate

# Modelo recomendado para CPU <8GB: qwen2.5:3b (melhor PT) ou llama3.2 (atual)
# Para GPU ou 16GB+ RAM: qwen2.5:7b ou mistral:7b
# Para baixar: ollama pull qwen2.5:3b
OLLAMA_MODEL=qwen2.5:3b

# Configurações de geração
OLLAMA_TIMEOUT=45          # Segundos máximos de espera por resposta
OLLAMA_NUM_PREDICT=250     # Máximo de tokens gerados (~150-200 palavras)
OLLAMA_TEMPERATURE=0.7     # 0.0=determinístico, 1.0=criativo; 0.7=balanceado
OLLAMA_NUM_CTX=1024        # Janela de contexto (conservador para <8GB RAM)

# === WHISPER (Transcrição de Áudio) ===
# base: mais rápido, menor acurácia
# small: ~2x mais lento em CPU, mas significativamente mais preciso em PT
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
```

---

## 5. Resumo das Mudanças

| Arquivo | Mudança | Prioridade |
|---------|---------|-----------|
| `src/alfabot/main.py` | Threading no webhook POST | 🔴 Crítico |
| `src/alfabot/services/ai_service.py` | Parâmetros Ollama + prompt + timeout | 🟠 Alto |
| `src/alfabot/services/rag_service.py` | n_results: 2 → 3 | 🟠 Alto |
| `src/alfabot/services/voice_service.py` | Whisper por env var | 🟡 Médio |
| `.env.example` | Novas variáveis documentadas | 🟡 Médio |

**Modelo recomendado**: trocar `OLLAMA_MODEL` para `qwen2.5:3b` após `ollama pull qwen2.5:3b`

---

## 6. Verificação Pós-Implementação

1. **Webhook assíncrono**: verificar nos logs que o `"recebido"` aparece antes do log `"Enviando requisição para Ollama..."` — confirma que o 200 foi retornado antes do processamento
2. **Parâmetros Ollama**: rodar `scripts/testar_integracao_ia.py` e verificar resposta em PT, máximo ~200 palavras
3. **Whisper configurável**: setar `WHISPER_MODEL=small` no `.env` e confirmar que o modelo carrega sem erro
4. **Teste concorrência**: enviar 2 mensagens simultâneas e confirmar processamento paralelo sem bloqueio
5. **Regressão**: todas as funcionalidades existentes (texto, áudio, níveis pedagógicos) devem continuar funcionando
