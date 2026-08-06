"""
Serviço de Transcrição de Áudio (STT) - NVIDIA Parakeet TDT
==========================================================
Responsável por converter ficheiros de áudio locais em texto utilizando
o modelo de ASR da NVIDIA (parakeet-tdt-0.6b-v3).
"""

import os
import threading
from dotenv import load_dotenv
from curumim.logger_config import logger

load_dotenv()

_stt_model = None
_stt_lock = threading.Lock()


def _get_model():
    """Carrega o modelo NVIDIA Parakeet TDT apenas na primeira transcrição."""
    global _stt_model
    if _stt_model is not None:
        return _stt_model
    with _stt_lock:
        if _stt_model is None:
            import torch
            from nemo.collections.asr.models import ASRModel

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"A carregar o modelo nvidia/parakeet-tdt-0.6b-v3 no dispositivo: {device}")
            _stt_model = ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3")
            _stt_model.to(device)
            _stt_model.eval()
            logger.info("Modelo Parakeet carregado com sucesso.")
    return _stt_model


def transcrever_audio(caminho_arquivo: str) -> str:
    """
    Transcreve um ficheiro de áudio local para texto utilizando o Parakeet TDT.
    
    Args:
        caminho_arquivo (str): Caminho local do ficheiro de áudio (fornecido pelo Node via media_ref).
        
    Returns:
        str: Texto transcrito limpo.
    """
    if not caminho_arquivo or not os.path.exists(caminho_arquivo):
        logger.error(f"Ficheiro de áudio não encontrado no caminho especificado: {caminho_arquivo}")
        return ""

    try:
        logger.info(f"A iniciar transcrição do ficheiro: {caminho_arquivo}")

        import torch
        modelo = _get_model()

        # O NeMo Parakeet aceita uma lista de caminhos de áudio para inferência
        with torch.inference_mode():
            transcriptions = modelo.transcribe([caminho_arquivo], batch_size=1)

        # O formato de retorno do NeMo pode vir encapsulado numa lista/tupla
        if transcriptions:
            texto_resultado = transcriptions[0]
            if isinstance(texto_resultado, list):
                texto_resultado = texto_resultado[0]
            
            texto_limpo = str(texto_resultado).strip()
            logger.info(f"Transcrição concluída com sucesso ({len(texto_limpo)} caracteres).")
            return texto_limpo

        return ""

    except Exception as e:
        logger.error(f"Erro ao processar a transcrição com Parakeet para o ficheiro {caminho_arquivo}: {e}")
        raise e