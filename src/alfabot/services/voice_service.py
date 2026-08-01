import os
import requests
from faster_whisper import WhisperModel
from src.alfabot.logger_config import logger

# Configurações centralizadas
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
TEMP_DIR = "data"

# Carrega o modelo apenas uma vez para economizar memória
# (O carregamento ocorre na importação deste módulo)
model = WhisperModel("base", device="cpu", compute_type="int8")


def baixar_audio(media_id: str) -> str:
    """
    Baixa o arquivo de áudio da API da Meta e salva na pasta de dados.
    """
    # Garante que a pasta 'data' exista antes de tentar salvar o arquivo
    os.makedirs(TEMP_DIR, exist_ok=True)

    url_media = f"https://graph.facebook.com/v20.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    try:
        # 1. Obter a URL de download
        response = requests.get(url_media, headers=headers, timeout=10)
        response.raise_for_status()  # Lança erro se a requisição falhar (4xx, 5xx)
        url_download = response.json()['url']

        # 2. Baixar o conteúdo do arquivo
        audio_response = requests.get(url_download, headers=headers, timeout=30)
        audio_response.raise_for_status()

        caminho_local = os.path.join(TEMP_DIR, f"temp_{media_id}.ogg")

        with open(caminho_local, "wb") as f:
            f.write(audio_response.content)

        logger.info(f"Áudio {media_id} baixado com sucesso em {caminho_local}")
        return caminho_local

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar áudio {media_id}: {e}")
        # Relançamos o erro para que o main.py saiba que o download falhou
        raise


def transcrever_audio(caminho_arquivo: str) -> str:
    """
    Transcreve o arquivo de áudio local para texto.
    """
    try:
        segments, _ = model.transcribe(caminho_arquivo, language="pt")
        texto = "".join([segment.text for segment in segments])
        return texto.strip()
    except Exception as e:
        logger.error(f"Erro ao transcrever o arquivo {caminho_arquivo}: {e}")
        return ""