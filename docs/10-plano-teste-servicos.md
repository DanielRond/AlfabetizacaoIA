# Plano de execução: teste manual dos serviços (STT + IA + TTS)

Teste manual do pipeline completo com a API do Gemini, registrado em
**09/ago/2026**. **Não concluído** — a tentativa de 09/ago (14:37–14:40,
terminal externo, áudio `Teste2.ogg`) foi abortada (ver abaixo).

## Por que está pendente

O processo Python foi **morto pelo OOM killer do Linux** durante o STT,
antes de terminar a transcrição. Confirmação no kernel
(`dmesg`/`journalctl`, 09/ago 14:40:09):

```
Out of memory: Killed process 85555 (python3) total-vm:10332272kB,
anon-rss:5334084kB
```

O Parakeet TDT (0,6B params, CPU, decodificador RNNT/TDT) chegou a
**~5,3 GB de RSS**; a máquina tem 7,6 GiB de RAM (3,0 GiB já em uso pelo
sistema) e 2,0 GiB de swap quase cheios. Rodar fora do VS Code resolveu o
crash da janela, mas não o estouro de memória.

## Como executar (quando a máquina permitir)

```bash
uv run python scripts/test_servicos.py data/audios/tts_f699ba8c76a544e89e92916c7a7ff99b.ogg
```

O argumento é o áudio de entrada (qualquer `.ogg` existente em `data/audios/`
serve como entrada de transcrição).

### Recomendações para evitar o crash

- Executar em um **terminal fora do VS Code** (ex.: GNOME Terminal), não na aba integrada.
- Fechar VS Code (ou pelo menos outras abas/aplicações pesadas) antes de rodar — libera RAM, mas sozinho pode não bastar (o Parakeet precisa de ~5,3 GB).
- Fechar o conector Node (`apps/whatsapp-connector`) se estiver rodando, para liberar RAM.
- Não rodar a suíte pytest em paralelo.

### Se o OOM persistir

- **Adicionar swap** (~4 GB) e tentar de novo; ou
- **Trocar para a variante CTC** do Parakeet (`nvidia/parakeet-ctc-0.6b`),
  que não usa decodificador RNNT e consome bem menos RAM — mudança de uma
  linha em `src/curumim/services/stt_service.py:31` (mesmo pacote NeMo, sem `uv sync`).

## O que o teste faz

1. **STT** (Parakeet): transcreve `data/audios/tts_f699...ogg` para texto.
2. **IA** (Gemini): `gerar_resposta_ia()` com a transcrição como pergunta.
3. **TTS** (Kokoro): sintetiza a resposta em `data/audios/tts_<uuid>.ogg`.

## Critérios de sucesso

- Log `Pipeline completo: STT -> IA -> TTS executado com sucesso.` e saída `0`.
- `--- TRANSCRIÇÃO ---` com texto não vazio.
- `--- RESPOSTA DA IA ---` diferente do fallback
  (`"Desculpe, estou com dificuldades para pensar agora..."`).
- `--- ÁUDIO GERADO ---` apontando para um `.ogg` novo em `data/audios/`.
