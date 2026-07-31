from unittest.mock import patch, MagicMock
from alfabot.services.whatsapp_service import (
    _formatar_markdown_para_whatsapp,
    enviar_mensagem_texto,
)


def test_negrito_duplo_vira_negrito_simples():
    resultado = _formatar_markdown_para_whatsapp("Isso é **muito importante** aqui.")
    assert resultado == "Isso é *muito importante* aqui."


def test_italico_underscore_nao_muda():
    resultado = _formatar_markdown_para_whatsapp("Isso é _itálico_ mesmo.")
    assert "_itálico_" in resultado


def test_lista_com_negrito():
    entrada = "* **No transporte:** servem para carregar cargas."
    resultado = _formatar_markdown_para_whatsapp(entrada)
    assert resultado == "- *No transporte:* servem para carregar cargas."


@patch("alfabot.services.whatsapp_service.requests.post")
def test_enviar_mensagem_texto_converte_antes_de_enviar(mock_post, monkeypatch):
    monkeypatch.setattr("alfabot.services.whatsapp_service.WHATSAPP_TOKEN", "fake-token")
    monkeypatch.setattr("alfabot.services.whatsapp_service.WHATSAPP_PHONE_ID", "123")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    enviar_mensagem_texto("5511999999999", "Isso é **importante**.")

    payload_enviado = mock_post.call_args.kwargs["json"]
    assert payload_enviado["text"]["body"] == "Isso é *importante*."
