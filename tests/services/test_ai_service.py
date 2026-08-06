from curumim.services import ai_service


def test_ollama_envia_prompt_e_retorna_resposta(monkeypatch):
    chamadas = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "resposta do ollama"}

    def fake_post(url, json, timeout):
        chamadas["url"] = url
        chamadas["json"] = json
        return FakeResponse()

    monkeypatch.setattr(ai_service, "PROVIDER", "ollama")
    monkeypatch.setattr(ai_service, "buscar_contexto", lambda *a, **k: "")
    monkeypatch.setattr("requests.post", fake_post)

    resultado = ai_service.gerar_resposta_ia("pergunta", "iniciante")

    assert resultado == "resposta do ollama"
    assert chamadas["url"] == ai_service.OLLAMA_URL
    assert "pergunta" in chamadas["json"]["prompt"]
    assert chamadas["json"]["model"] == ai_service.OLLAMA_MODEL


def test_gemini_usa_cliente(monkeypatch):
    chamadas = {}

    class FakeModels:
        def generate_content(self, model, contents):
            chamadas["model"] = model
            chamadas["contents"] = contents
            return type("Resp", (), {"text": "resposta do gemini"})()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(ai_service, "PROVIDER", "gemini")
    monkeypatch.setattr(ai_service, "buscar_contexto", lambda *a, **k: "")
    monkeypatch.setattr(ai_service, "_get_gemini_client", lambda: FakeClient())

    resultado = ai_service.gerar_resposta_ia("pergunta")

    assert resultado == "resposta do gemini"
    assert chamadas["model"] == ai_service.GEMINI_MODEL
    assert "pergunta" in chamadas["contents"]


def test_fallback_quando_provedor_falha(monkeypatch):
    def falhar(*args, **kwargs):
        raise RuntimeError("timeout")

    monkeypatch.setattr(ai_service, "PROVIDER", "ollama")
    monkeypatch.setattr(ai_service, "buscar_contexto", lambda *a, **k: "")
    monkeypatch.setattr("requests.post", falhar)

    resultado = ai_service.gerar_resposta_ia("pergunta")

    assert "Desculpe" in resultado
