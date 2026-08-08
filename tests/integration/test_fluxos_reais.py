"""
Testes de integração reais (requerem serviços externos).

Rodar explicitamente com: uv run pytest -m integration
"""

import os

import pytest
import requests

from curumim.services import ai_service, rag_service, tts_service

pytestmark = pytest.mark.integration

FALLBACK_IA = "Desculpe, estou com dificuldades para pensar agora. Pode tentar novamente?"


def _rag_tem_documentos() -> bool:
    try:
        return rag_service._get_collection().count() > 0
    except Exception:
        return False


def _ia_provedor_disponivel() -> bool:
    if ai_service.PROVIDER == "gemini":
        chave = os.getenv("GEMINI_API_KEY", "")
        # Aceita chaves de API (AIza...) e tokens OAuth (AQ...): a validade é
        # confirmada pelo próprio teste, que falha se a chamada real falhar.
        return len(chave) >= 20
    url = ai_service.OLLAMA_URL.replace("/api/generate", "/api/tags")
    try:
        requests.get(url, timeout=5).raise_for_status()
        return True
    except Exception:
        return False


def test_tts_fluxo_real():
    if not tts_service.tts_disponivel():
        pytest.skip("Modelos Kokoro não encontrados em models/")

    caminho = tts_service.sintetizar_fala("Olá, vamos aprender sobre o Marajó.")

    assert caminho is not None
    assert caminho.endswith(".ogg")


def test_rag_fluxo_real():
    if not _rag_tem_documentos():
        pytest.skip("ChromaDB vazio. Popule com: uv run python scripts/ingest_knowledge.py")

    contexto = rag_service.buscar_contexto("O que é o Marajó?")

    assert contexto.strip()


def test_ia_fluxo_real():
    if not _ia_provedor_disponivel():
        pytest.skip("Provedor de IA indisponível (Ollama fora do ar ou GEMINI_API_KEY inválida).")

    resposta = ai_service.gerar_resposta_ia("O que são os búfalos na ilha do Marajó?")

    assert resposta
    assert resposta != FALLBACK_IA


def test_conversa_ia_mais_tts():
    if not _ia_provedor_disponivel():
        pytest.skip("Provedor de IA indisponível (Ollama fora do ar ou GEMINI_API_KEY inválida).")

    resposta = ai_service.gerar_resposta_ia("O que é a lenda da Cobra Grande?")

    assert resposta
    assert resposta != FALLBACK_IA

    if tts_service.tts_disponivel():
        caminho = tts_service.sintetizar_fala(resposta)
        assert caminho is not None
