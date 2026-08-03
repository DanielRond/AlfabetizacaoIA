import os
import re
import subprocess
import uuid
import threading
from dotenv import load_dotenv
from curumim.logger_config import logger

# Garante que o .env já foi carregado antes de ler as variáveis abaixo,
# independente da ordem de import de quem chama este módulo.
load_dotenv()

TEMP_DIR = "data/audios"
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
TTS_VOICE = os.getenv("TTS_VOICE", "pf_dora")
KOKORO_MODEL_PATH = os.getenv("KOKORO_MODEL_PATH", "models/kokoro-v1.0.onnx")
KOKORO_VOICES_PATH = os.getenv("KOKORO_VOICES_PATH", "models/voices-v1.0.bin")
ESPEAK_LIB_PATH = "/lib/x86_64-linux-gnu/libespeak-ng.so.1"
ESPEAK_DATA_PATH = "/usr/lib/x86_64-linux-gnu/espeak-ng-data"

_kokoro_instance = None
_kokoro_lock = threading.Lock()

# --- Limpeza de Markdown/emoji para leitura natural pelo Kokoro ---
_MD_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_MD_ITALIC_AST_RE = re.compile(r'(?<!\*)(?<!\w)\*([^\s*][^*]*?)\*(?!\w)')
_MD_ITALIC_UNDER_RE = re.compile(r'(?<!\w)_([^\s_][^_]*?)_(?!\w)')
_MD_HEADER_RE = re.compile(r'(?m)^#{1,6}[ \t]+')
_MD_LIST_ITEM_RE = re.compile(r'(?m)^[ \t]*(?:[*\-+]|\d+\.)[ \t]+(.*)$')
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF"
    "️‍"
    "]+",
    flags=re.UNICODE,
)
_SPACE_BEFORE_PUNCT_RE = re.compile(r'[ \t]+([.!?,;:])')
_MULTI_SPACE_RE = re.compile(r'[ \t]{2,}')


def _limpar_texto_para_audio(texto: str) -> str:
    """Remove marcação Markdown e emojis antes de mandar pro Kokoro,
    convertendo itens de lista em frases separadas por ponto."""
    if not texto:
        return texto
    t = texto
    t = _MD_BOLD_RE.sub(r'\1', t)
    t = _MD_ITALIC_AST_RE.sub(r'\1', t)
    t = _MD_ITALIC_UNDER_RE.sub(r'\1', t)
    t = _MD_HEADER_RE.sub('', t)
    t = _MD_LIST_ITEM_RE.sub(r'\1', t)
    t = _EMOJI_RE.sub('', t)
    t = t.replace('**', '')  # fallback para "**" desbalanceado (resposta truncada)

    linhas = [l.strip() for l in t.split('\n') if l.strip()]
    linhas = [l if l[-1] in '.!?:;,' else l + '.' for l in linhas]
    t = ' '.join(linhas)

    t = _SPACE_BEFORE_PUNCT_RE.sub(r'\1', t)
    t = _MULTI_SPACE_RE.sub(' ', t)
    return t.strip()


def _carregar_kokoro():
    global _kokoro_instance
    if _kokoro_instance is not None:
        return _kokoro_instance
    with _kokoro_lock:
        if _kokoro_instance is None:
            if not (os.path.exists(KOKORO_MODEL_PATH) and os.path.exists(KOKORO_VOICES_PATH)):
                logger.error("Modelos do Kokoro não encontrados em 'models/'.")
                return None
            from kokoro_onnx import Kokoro
            from kokoro_onnx.config import EspeakConfig
            espeak_config = EspeakConfig(lib_path=ESPEAK_LIB_PATH, data_path=ESPEAK_DATA_PATH)
            _kokoro_instance = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH, espeak_config=espeak_config)
    return _kokoro_instance


def tts_disponivel() -> bool:
    return TTS_ENABLED and os.path.exists(KOKORO_MODEL_PATH) and os.path.exists(KOKORO_VOICES_PATH)


def sintetizar_fala(texto: str) -> str | None:
    """Gera um .ogg (Opus) a partir do texto. Retorna o caminho, ou None em qualquer falha."""
    kokoro = _carregar_kokoro()
    if kokoro is None:
        return None

    texto_limpo = _limpar_texto_para_audio(texto)
    if not texto_limpo:
        logger.warning("Texto vazio após limpeza para áudio; síntese abortada.")
        return None

    os.makedirs(TEMP_DIR, exist_ok=True)
    ident = uuid.uuid4().hex
    caminho_wav = os.path.join(TEMP_DIR, f"tts_{ident}.wav")
    caminho_ogg = os.path.join(TEMP_DIR, f"tts_{ident}.ogg")

    try:
        import soundfile as sf
        samples, sample_rate = kokoro.create(texto_limpo, voice=TTS_VOICE, speed=1.0, lang="pt-br")
        sf.write(caminho_wav, samples, sample_rate)

        subprocess.run(
            ["ffmpeg", "-y", "-i", caminho_wav, "-c:a", "libopus", "-b:a", "32k",
             "-ar", "24000", "-ac", "1", caminho_ogg],
            capture_output=True, check=True,
        )
        logger.info(f"Áudio de resposta gerado em {caminho_ogg}")
        return caminho_ogg

    except Exception as e:
        logger.error(f"Erro ao sintetizar fala: {e}")
        return None

    finally:
        if os.path.exists(caminho_wav):
            os.remove(caminho_wav)
