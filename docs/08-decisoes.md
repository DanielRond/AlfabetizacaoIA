# 08 — Decisões Arquiteturais (ADRs)

Registro das decisões de design mais relevantes. Cada ADR segue o formato
**Contexto → Decisão → Consequências**. As decisões originais do split estão em
[`specs/002-whatsappjs-python-split/research.md`](../specs/002-whatsappjs-python-split/research.md).

## ADR-001 — Dois serviços independentes (Node + Python)

- **Contexto**: o WhatsApp precisa de transporte baseado em sessão (QR login,
  reconexão), e o processamento pedagógico é pesado em Python (IA/RAG/STT/TTS).
- **Decisão**: um conector **Node.js** (whatsapp-web.js) é dono do transporte e um
  **backend Python** (Flask) é dono do processamento. Fronteiras estritas: o Node não
  conhece regras pedagógicas; o Python não fala com a Meta.
- **Consequências**: cada serviço evolui e escala independentemente; o custo é manter
  o contrato entre eles estável e a operação de dois processos.
- **Alternativas rejeitadas**: manter Meta Cloud API webhook (removida pelo requisito);
  transportar o WhatsApp para Python via wrapper (transport concern isola-se melhor no Node).

## ADR-002 — Contrato HTTP versionado em vez de fila

- **Contexto**: Node e Python precisam trocar mensagens e respostas.
- **Decisão**: usar um **pequeno HTTP API** com envelope versionado
  (`/v1/messages/*`). A `action` da resposta é a fonte da verdade para o envio.
- **Consequências**: simples, debuggável e testável localmente; sem operação de
  broker. Em escala futura, uma fila pode entrar sem mudar o envelope.
- **Alternativas rejeitadas**: fila (overhead operacional, dev local mais difícil);
  chamadas processo-a-processo (dificultam deploy e observação independentes).

## ADR-003 — Mídia por referência, não por base64

- **Contexto**: áudio é grande demais para JSON limpo.
- **Decisão**: o Node salva mídia de entrada em disco (`data/media_in/`) e troca apenas
  `media_ref`; o Python escreve áudios em `data/audios/` e devolve o caminho; o Node
  resolve e publica. Sem embutir base64 no happy path.
- **Consequências**: payloads pequenos, fáceis de retentar e inspecionar; exige
  storage/filesystem compartilhado entre os serviços.
- **Alternativas rejeitadas**: base64 no JSON (infla payload e complica retry);
  streaming via API (complexidade extra na primeira iteração).

## ADR-004 — Backend Python mantém toda a inteligência

- **Contexto**: o código de IA já existe em Python.
- **Decisão**: perfil, onboarding, RAG, STT, prompt, geração e TTS continuam no Python.
- **Consequências**: domínio concentrado em um lugar; o Node fica enxuto.
- **Alternativas rejeitadas**: migrar IA para Node (duplicaria a stack e aumentaria manutenção).

## ADR-005 — Testes de contrato na fronteira

- **Contexto**: os novos modos de falha concentram-se na fronteira Node→Python.
- **Decisão**: fixtures JSON de contrato + testes de contrato dos dois lados
  (`tests/contract/test_contrato.py` e `apps/whatsapp-connector/tests/contract.test.js`),
  além dos unitários por módulo.
- **Consequências**: melhor sinal de regressão por esforço; mudanças no contrato são
  pegas nos dois lados.
- **Alternativas rejeitadas**: só E2E (mais lento, regressão de fronteira difícil de isolar).

## ADR-006 — Lazy-load de modelos pesados (STT/TTS)

- **Contexto**: Parakeet (STT) e Kokoro (TTS) são modelos grandes; carregar no startup
  atrasa o boot e gasta memória mesmo sem uso.
- **Decisão**: carregamento sob demanda com `threading.Lock` (ex.: `_get_model`,
  `_carregar_kokoro`). O cliente Gemini também é lazy.
- **Consequências**: boot rápido e memória só quando o recurso é usado; primeira
  chamada paga o custo de carga.

## ADR-007 — Resiliência no conector: retry, backoff e fallback

- **Contexto**: falhas de rede, backend fora e áudio corrompido não podem derrubar o serviço.
- **Decisão**:
  - `postInbound`: retry com backoff exponencial; **4xx não são retentados**;
  - `postDelivered`: fire-and-forget (nunca falha o pipeline);
  - reconexão da sessão com backoff (5 s → 60 s, máx. 10 tentativas, `exit(1)` no fim);
  - áudio incompreensível → `request_retry` + fallback gentil (sem resposta inventada).
- **Consequências**: operação resiliente por mensagem; o orquestrador pode recuperar o
  processo após esgotamento.

## ADR-008 — Áudio de resposta por nível pedagógico

- **Contexto**: reforço de áudio é valioso para iniciantes, mas custoso para todos.
- **Decisão**: `deve_incluir_audio` — `iniciante` → sempre áudio; `basico` → áudio se o
  aluno mandou áudio; `intermediario` → texto.
- **Consequências**: experiência adaptada ao perfil; menos síntese TTS para níveis
  avançados (economia de CPU).

## ADR-009 — Rastreio ponta a ponta com `correlation_id`

- **Contexto**: a spec exige correlacionar o evento do WhatsApp ao processamento no
  Python e ao envio no Node (FR-010).
- **Decisão**: UUID gerado no Node acompanha o payload, os logs (Pino/Loguru) e o
  `InteractionRecord` no SQLite; o ack `delivered` fecha o ciclo (outbound `sent`/`failed`).
- **Consequências**: reconstrução completa de qualquer interação; pequena sobrecarga
  de escrita no banco por mensagem.

## ADR-010 — Migração de banco idempotente

- **Contexto**: banco SQLite local; colunas novas (`display_name`, `last_seen_at`)
  precisam ser adicionadas sem quebrar bancos existentes.
- **Decisão**: `inicializar_banco()` roda no `create_app()` com `create_all` +
  `ALTER TABLE` condicional (coluna não existente).
- **Consequências**: deploy seguro e reexecutável; sem framework de migração adicional
  nesta fase.

## ADR-011 — Banco real em `src/data/curumim.db`

- **Contexto**: localização confusa do banco entre `data/` e `src/data/`.
- **Decisão**: `PROJECT_ROOT = Path(__file__).resolve().parents[2]` resolve para
  `src/`, logo o banco é `src/data/curumim.db`. `*.db` é ignorado pelo git.
- **Consequências**: o banco não é versionado; quem aponta o código para `data/`
  deve usar o caminho resolvido pelo próprio `database.py`.
