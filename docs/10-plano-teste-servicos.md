# Plano de execução: teste manual dos serviços (STT + IA + TTS)

Teste manual do pipeline completo com a API do Gemini, registrado em
**09/ago/2026**. Ainda **não executado** (ver aviso abaixo).

## Por que está pendente

Cada tentativa de execução pela aba do VS Code derrubou a janela (provável
falta de memória: carregar o modelo Parakeet STT consome vários GB de RAM).

## Como executar (quando a máquina permitir)

```bash
uv run python scripts/test_servicos.py data/audios/tts_f699ba8c76a544e89e92916c7a7ff99b.ogg
```

O argumento é o áudio de entrada (qualquer `.ogg` existente em `data/audios/`
serve como entrada de transcrição).

### Recomendações para evitar o crash

- Executar em um **terminal fora do VS Code** (ex.: GNOME Terminal), não na aba integrada.
- Fechar VS Code (ou pelo menos outras abas/aplicações pesadas) antes de rodar.
- Fechar o conector Node (`apps/whatsapp-connector`) se estiver rodando, para liberar RAM.
- Não rodar a suíte pytest em paralelo.

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
