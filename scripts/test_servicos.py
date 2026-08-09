"""
Teste manual dos serviços STT, IA e TTS usando um arquivo de áudio local.

Pipeline: áudio (.ogg) -> STT (Parakeet) -> IA (Gemini) -> TTS (Kokoro)

Uso:
    uv run python scripts/test_servicos.py [caminho_do_audio]
"""

import os
import subprocess
import sys
import tempfile

from loguru import logger

from curumim.services.ai_service import gerar_resposta_ia
from curumim.services.stt_service import transcrever_audio
from curumim.services.tts_service import sintetizar_fala

FALLBACK_IA = "Desculpe, estou com dificuldades para pensar agora. Pode tentar novamente?"


def _converter_para_wav(origem: str) -> str:
    """Converte o áudio para WAV mono 16 kHz (formato ideal para o Parakeet)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        destino = tmp.name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", origem, "-ar", "16000", "-ac", "1", destino],
            capture_output=True, check=True,
        )
        return destino
    except subprocess.CalledProcessError as e:
        os.remove(destino)
        detalhe = e.stderr.decode(errors="replace") if e.stderr else str(e)
        raise RuntimeError(f"ffmpeg não conseguiu converter o áudio: {detalhe}") from e


def testar_stt(caminho_audio: str) -> str:
    logger.info(f"=== STT: transcrevendo {caminho_audio} ===")
    try:
        texto = transcrever_audio(caminho_audio)
    except Exception as e:
        logger.warning(f"Falha ao decodificar o áudio diretamente ({e}); tentando via WAV...")
        wav = _converter_para_wav(caminho_audio)
        try:
            texto = transcrever_audio(wav)
        finally:
            os.remove(wav)

    if not texto:
        raise RuntimeError("STT retornou texto vazio")
    logger.success(f"STT OK ({len(texto)} caracteres)")
    print(f"\n--- TRANSCRIÇÃO ---\n{texto}\n")
    return texto


def testar_ia(pergunta: str) -> str:
    logger.info("=== IA: gerando resposta via Gemini ===")
    resposta = gerar_resposta_ia(pergunta)
    if not resposta or resposta == FALLBACK_IA:
        raise RuntimeError("IA retornou resposta vazia ou fallback de erro")
    logger.success("IA OK")
    print(f"\n--- RESPOSTA DA IA ---\n{resposta}\n")
    return resposta


def testar_tts(texto: str) -> str:
    logger.info("=== TTS: sintetizando fala via Kokoro ===")
    caminho = sintetizar_fala(texto)
    if not caminho:
        raise RuntimeError("TTS falhou (retornou None)")
    logger.success(f"TTS OK: {caminho}")
    print(f"\n--- ÁUDIO GERADO ---\n{caminho}\n")
    return caminho


def main() -> int:
    caminho_audio = sys.argv[1] if len(sys.argv) > 1 else "teste_audio.ogg"
    if not os.path.exists(caminho_audio):
        logger.error(f"Arquivo de áudio não encontrado: {caminho_audio}")
        return 1

    try:
        texto = testar_stt(caminho_audio)
        resposta = testar_ia(texto)
        testar_tts(resposta)
    except Exception as e:
        logger.error(f"Teste falhou: {e}")
        return 1

    logger.success("Pipeline completo: STT -> IA -> TTS executado com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
