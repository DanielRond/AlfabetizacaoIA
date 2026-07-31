import os
import requests
from dotenv import load_dotenv
import re

# Importação do logger unificado do seu projeto
from alfabot.logger_config import logger

# Garante que o .env já foi carregado antes de ler as variáveis abaixo,
# independente da ordem de import de quem chama este módulo.
load_dotenv()

# Configurações centralizadas no topo do módulo (evita ler o .env a cada mensagem)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_API_VERSION = "v20.0"

_MD_HEADER_RE = re.compile(r'(?m)^#{1,6}[ \t]+')
_MD_LIST_MARKER_RE = re.compile(r'(?m)^([ \t]*)[*\-+][ \t]+')
_MD_BOLD_TO_WA_RE = re.compile(r'\*\*(.+?)\*\*')


def _formatar_markdown_para_whatsapp(texto: str) -> str:
    """Converte negrito Markdown (**texto**) para a sintaxe do WhatsApp (*texto*).
    Itálico com _texto_ já é compatível e não precisa de conversão."""
    if not texto:
        return texto
    t = texto
    t = _MD_HEADER_RE.sub('', t)
    t = _MD_LIST_MARKER_RE.sub(r'\1- ', t)
    t = _MD_BOLD_TO_WA_RE.sub(r'*\1*', t)
    t = t.replace('**', '*')  # fallback para "**" desbalanceado
    return t


def enviar_mensagem_texto(phone_number: str, texto: str) -> bool:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.error("WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID não configurados no arquivo .env")
        return False

    texto = _formatar_markdown_para_whatsapp(texto)

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": texto}
    }

    try:
        # Faz o envio com timeout de segurança de 10 segundos
        resposta = requests.post(url, headers=headers, json=payload, timeout=10)

        # Dispara automaticamente um HTTPError se o status code for 4xx ou 5xx
        resposta.raise_for_status()

        logger.info(f"Mensagem enviada com sucesso para {phone_number}!")
        return True

    except requests.exceptions.HTTPError as e:
        # Captura erros retornados pela própria API da Meta (ex: número inválido, token expirado)
        status_code = e.response.status_code if e.response else "N/A"
        error_text = e.response.text if e.response else str(e)
        logger.error(f"Erro HTTP da Meta ao enviar para {phone_number}: {status_code} - {error_text}")
        return False

    except requests.exceptions.RequestException as e:
        # Captura erros de rede/infraestrutura (ex: queda de internet, DNS falhou)
        logger.error(f"Erro de conexão/rede com a API da Meta ao tentar enviar para {phone_number}: {e}")
        return False


def _fazer_upload_midia(caminho_arquivo: str, mime_type: str = "audio/ogg") -> str | None:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.error("WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID não configurados no arquivo .env")
        return None

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    try:
        with open(caminho_arquivo, "rb") as f:
            files = {"file": (os.path.basename(caminho_arquivo), f, mime_type)}
            data = {"messaging_product": "whatsapp", "type": mime_type}
            resposta = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        resposta.raise_for_status()
        return resposta.json().get("id")

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao subir mídia de áudio: {e}")
        return None


def enviar_mensagem_audio(phone_number: str, caminho_audio: str) -> bool:
    media_id = _fazer_upload_midia(caminho_audio)
    if not media_id:
        return False

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": phone_number, "type": "audio", "audio": {"id": media_id}}

    try:
        resposta = requests.post(url, headers=headers, json=payload, timeout=10)
        resposta.raise_for_status()
        logger.info(f"Áudio enviado com sucesso para {phone_number}!")
        return True
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "N/A"
        error_text = e.response.text if e.response else str(e)
        logger.error(f"Erro HTTP da Meta ao enviar áudio para {phone_number}: {status_code} - {error_text}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de conexão/rede ao enviar áudio para {phone_number}: {e}")
        return False
