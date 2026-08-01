import os
import requests

# Importação do logger unificado do seu projeto
from src.alfabot.logger_config import logger

# Configurações centralizadas no topo do módulo (evita ler o .env a cada mensagem)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_API_VERSION = "v20.0"


def enviar_mensagem_texto(phone_number: str, texto: str) -> bool:
    """
    Envia uma mensagem de texto simples via WhatsApp Cloud API.

    Retorna True se enviada com sucesso, False caso contrário.
    """
    # Validação rápida das credenciais configuradas
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.error("WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID não configurados no arquivo .env")
        return False

    # Montagem dos dados da requisição
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