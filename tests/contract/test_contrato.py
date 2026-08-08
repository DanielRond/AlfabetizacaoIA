"""
Testes de contrato Node <-> Python.

Usa as fixtures JSON definidas em
specs/002-whatsappjs-python-split/contracts/fixtures/ para validar que o
backend aceita o payload de entrada e devolve o envelope de resposta conforme
o contrato, além do endpoint de entrega.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import curumim.main as main_module
from curumim.models.database import Base, LearnerProfile, InteractionRecord


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "specs" / "002-whatsappjs-python-split" / "contracts" / "fixtures"

RESPONSE_ENVELOPE_KEYS = {"correlation_id", "action", "text", "media_ref", "media_type", "status", "error_code"}
DELIVERED_STATUS_KEYS = {"status"}


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
    return main_module.create_app().test_client()


def _carregar(nome: str) -> dict:
    return json.loads((FIXTURES_DIR / nome).read_text(encoding="utf-8"))


@patch("curumim.main.gerar_resposta_ia", return_value="Resposta pedagogica de teste.")
def test_inbound_aceita_fixture_e_retorna_envelope_do_contrato(mock_ia, client):
    payload = _carregar("inbound-message.json")

    resp = client.post("/v1/messages/inbound", json=payload)

    assert resp.status_code == 200
    data = resp.get_json()
    assert RESPONSE_ENVELOPE_KEYS <= set(data.keys())
    assert data["correlation_id"] == payload["correlation_id"]
    assert data["status"] == "ok"


def test_inbound_fixture_gera_interaction_record(client, db_session_factory):
    payload = _carregar("inbound-message.json")

    with patch("curumim.main.gerar_resposta_ia", return_value="Resposta pedagogica de teste."):
        resp = client.post("/v1/messages/inbound", json=payload)
    assert resp.status_code == 200

    with db_session_factory() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number=payload["phone_number"]).first()
        assert aluno is not None
        interacoes = session.query(InteractionRecord).filter_by(profile_id=aluno.id).all()
        assert any(i.direction == "inbound" and i.correlation_id == payload["correlation_id"] for i in interacoes)


def test_delivered_aceita_fixture_e_retorna_ok(client, db_session_factory):
    payload = _carregar("inbound-message.json")
    delivered = _carregar("delivered.json")

    with patch("curumim.main.gerar_resposta_ia", return_value="Resposta pedagogica de teste."):
        client.post("/v1/messages/inbound", json=payload)

    resp = client.post("/v1/messages/delivered", json=delivered)

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}

    with db_session_factory() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number=payload["phone_number"]).first()
        outbound = (
            session.query(InteractionRecord)
            .filter_by(profile_id=aluno.id, direction="outbound", correlation_id=delivered["correlation_id"])
            .all()
        )
        assert len(outbound) >= 1
        assert outbound[-1].status == "sent"


def test_delivered_payload_invalido_retorna_400(client):
    resp = client.post("/v1/messages/delivered", json={"correlation_id": None, "status": "xyz"})
    assert resp.status_code == 400
