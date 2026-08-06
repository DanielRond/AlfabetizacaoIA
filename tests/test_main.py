import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import curumim.main as main_module
from curumim.models.database import Base, LearnerProfile, ChatMessage


@pytest.fixture
def db_session_factory(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(main_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(main_module, "inicializar_banco", lambda: None)

    return TestSessionLocal


@pytest.fixture
def client(db_session_factory):
    app = main_module.create_app()
    return app.test_client()


def _payload(**overrides):
    data = {
        "correlation_id": "trace-1",
        "message_id": "msg-1",
        "phone_number": "5591999999999",
        "message_type": "text",
        "text": "olá",
        "media_ref": None,
        "received_at": "2026-08-06T12:00:00Z",
        "metadata": {},
    }
    data.update(overrides)
    return data


def _criar_aluno(db_session_factory, phone_number="5591999999999", level="intermediario"):
    with db_session_factory() as session:
        aluno = LearnerProfile(
            phone_number=phone_number,
            pedagogical_level=level,
            onboarding_state="active",
        )
        session.add(aluno)
        session.commit()
        return aluno.id


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "healthy"


def test_json_ausente_retorna_400(client):
    resp = client.post("/v1/messages/inbound", json=None)
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "INVALID_JSON_PAYLOAD"


def test_campos_obrigatorios_ausentes_retornam_400(client):
    resp = client.post("/v1/messages/inbound", json={"correlation_id": "x"})
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "MISSING_REQUIRED_FIELDS"


@patch("curumim.main.gerar_resposta_ia", return_value="Resposta pedagógica de teste.")
def test_texto_de_aluno_ativo_retorna_send_text(mock_ia, client, db_session_factory):
    aluno_id = _criar_aluno(db_session_factory)

    resp = client.post("/v1/messages/inbound", json=_payload(text="o que é a ilha de marajó?"))

    data = resp.get_json()
    assert resp.status_code == 200
    assert data["action"] == "send_text"
    assert data["status"] == "ok"
    assert data["correlation_id"] == "trace-1"
    assert data["text"] == "Resposta pedagógica de teste."
    assert data["media_type"] is None
    mock_ia.assert_called_once()

    with db_session_factory() as session:
        mensagens = (
            session.query(ChatMessage)
            .filter_by(learner_id=aluno_id)
            .order_by(ChatMessage.id)
            .all()
        )
        assert [m.sender for m in mensagens] == ["user", "assistant"]


def test_primeiro_contato_abre_onboarding(client, db_session_factory):
    resp = client.post("/v1/messages/inbound", json=_payload(text="oi"))

    data = resp.get_json()
    assert data["action"] == "send_text"
    assert data["status"] == "ok"
    assert "iniciante, básico ou intermediário" in data["text"]

    with db_session_factory() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number="5591999999999").first()
        assert aluno is not None
        assert aluno.onboarding_state == "collecting_level"


def test_escolha_de_nivel_ativa_perfil(client, db_session_factory):
    client.post("/v1/messages/inbound", json=_payload(text="oi"))

    resp = client.post(
        "/v1/messages/inbound",
        json=_payload(correlation_id="trace-2", message_id="msg-2", text="básico"),
    )

    data = resp.get_json()
    assert data["status"] == "ok"
    assert "Registrei seu nível" in data["text"]

    with db_session_factory() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number="5591999999999").first()
        assert aluno.onboarding_state == "active"
        assert aluno.pedagogical_level == "basico"


def test_nivel_invalido_mantem_coleta(client, db_session_factory):
    client.post("/v1/messages/inbound", json=_payload(text="oi"))

    resp = client.post(
        "/v1/messages/inbound",
        json=_payload(correlation_id="trace-2", message_id="msg-2", text="sei lá"),
    )

    assert "Não entendi" in resp.get_json()["text"]

    with db_session_factory() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number="5591999999999").first()
        assert aluno.onboarding_state == "collecting_level"


def test_audio_sem_arquivo_retorna_request_retry(client):
    resp = client.post(
        "/v1/messages/inbound",
        json=_payload(message_type="audio", media_ref="C:/nao/existe.ogg"),
    )

    data = resp.get_json()
    assert data["action"] == "request_retry"
    assert data["status"] == "retry"
    assert data["error_code"] == "MEDIA_FILE_NOT_FOUND"


@patch("curumim.main.gerar_resposta_ia", return_value="Resposta com áudio.")
@patch("curumim.main.sintetizar_fala")
@patch("curumim.main.tts_disponivel", return_value=True)
@patch("curumim.main.transcrever_audio", return_value="uma frase transcrita")
def test_audio_de_aluno_ativo_retorna_send_audio(
    mock_transcricao, mock_tts, mock_sintetizar, mock_ia, client, db_session_factory, tmp_path
):
    aluno_id = _criar_aluno(db_session_factory, level="iniciante")

    entrada = tmp_path / "in.ogg"
    saida = tmp_path / "tts_out.ogg"
    entrada.write_bytes(b"fake")
    saida.write_bytes(b"fake")
    mock_sintetizar.return_value = str(saida)

    resp = client.post(
        "/v1/messages/inbound",
        json=_payload(message_type="audio", media_ref=str(entrada)),
    )

    data = resp.get_json()
    assert data["action"] == "send_audio"
    assert data["status"] == "ok"
    assert data["media_type"] == "audio"
    assert data["media_ref"] == str(saida)

    with db_session_factory() as session:
        mensagens = (
            session.query(ChatMessage)
            .filter_by(learner_id=aluno_id)
            .order_by(ChatMessage.id)
            .all()
        )
        assert mensagens[0].message_type == "audio"


def test_imagem_retorna_recusa_amigavel(client, db_session_factory):
    resp = client.post("/v1/messages/inbound", json=_payload(message_type="image"))

    data = resp.get_json()
    assert data["action"] == "send_text"
    assert data["status"] == "ok"
    assert "não consigo ver" in data["text"]

    with db_session_factory() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number="5591999999999").first()
        assert aluno is not None
        assert session.query(ChatMessage).filter_by(learner_id=aluno.id).count() == 2
