import os
import requests
from loguru import logger
from src.alfabot.services.rag_service import buscar_contexto

# Configurações globais (carregadas uma vez na importação)
PROVIDER = os.getenv("IA_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Variável privada para o cliente Gemini
_gemini_client = None


def _get_gemini_client():
    """Inicializa o cliente Gemini apenas quando necessário."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no .env")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _gerar_com_ollama(prompt: str) -> str:
    """Envia requisição para o servidor Ollama local."""
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    # Segurança: garante que tratamos o retorno como string antes de usar strip()
    conteudo = response.json().get("response")
    return str(conteudo).strip() if conteudo else ""


def _gerar_com_gemini(prompt: str) -> str:
    """Envia requisição para a API do Gemini usando o cliente lazy-loaded."""
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    # Segurança: response.text pode ser None em casos de erro ou blocos de segurança
    conteudo = response.text
    return str(conteudo).strip() if conteudo else ""


def gerar_resposta_ia(mensagem_usuario: str, nivel_pedagogico: str = "iniciante") -> str:
    """Orquestra a busca de contexto e a geração da resposta pela IA."""
    logger.info(f"Buscando contexto para: '{mensagem_usuario}'")
    contexto = buscar_contexto(mensagem_usuario)

    prompt = f"""Você é um professor amigável e paciente, ensinando um aluno de nível {nivel_pedagogico}.
Use o CONTEXTO abaixo para responder à pergunta do aluno. Se a resposta não estiver no contexto, seja honesto e diga que não tem essa informação, mas tente ajudar de forma educativa.

CONTEXTO:
{contexto}

PERGUNTA:
{mensagem_usuario}

RESPOSTA:"""

    try:
        if PROVIDER == "gemini":
            logger.info("Enviando requisição para Gemini...")
            return _gerar_com_gemini(prompt)

        logger.info("Enviando requisição para Ollama...")
        return _gerar_com_ollama(prompt)

    except Exception as e:
        logger.error(f"Erro ao comunicar com o provedor {PROVIDER}: {e}")
        return "Desculpe, estou com dificuldades para pensar agora. Pode tentar novamente?"