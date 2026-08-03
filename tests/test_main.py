import pytest
from unittest.mock import patch
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

    return TestSessionLocal


@patch("curumim.main.enviar_mensagem_texto")
def test_registrar_tentativa_imagem_com_legenda(mock_enviar, db_session_factory):
    mensagem_info = {"image": {"id": "abc123", "caption": "olha essa foto"}}

    main_module.registrar_tentativa_imagem("5591999999999", mensagem_info)

    with db_session_factory() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number="5591999999999").first()
        assert aluno is not None

        mensagens = (
            session.query(ChatMessage)
            .filter_by(learner_id=aluno.id)
            .order_by(ChatMessage.id)
            .all()
        )
        assert len(mensagens) == 2
        assert mensagens[0].sender == "user"
        assert mensagens[0].message_type == "image"
        assert mensagens[0].content == "olha essa foto"
        assert mensagens[1].sender == "assistant"
        assert mensagens[1].message_type == "text"

    mock_enviar.assert_called_once()
    numero_chamado, texto_chamado = mock_enviar.call_args.args
    assert numero_chamado == "5591999999999"
    assert "não consigo ver sua imagem" in texto_chamado


@patch("curumim.main.enviar_mensagem_texto")
def test_registrar_tentativa_imagem_sem_legenda_usa_placeholder(mock_enviar, db_session_factory):
    mensagem_info = {"image": {"id": "abc123"}}

    main_module.registrar_tentativa_imagem("5591999999999", mensagem_info)

    with db_session_factory() as session:
        msg_usuario = session.query(ChatMessage).filter_by(sender="user").first()
        assert msg_usuario.content == "[imagem enviada]"


@patch("curumim.main.registrar_tentativa_imagem")
def test_processar_mensagem_whatsapp_roteia_imagem_para_a_funcao_certa(mock_registrar):
    mensagem_info = {"from": "5591999999999", "type": "image", "image": {"id": "abc123"}}

    main_module.processar_mensagem_whatsapp(mensagem_info)

    mock_registrar.assert_called_once_with("5591999999999", mensagem_info)


@patch("curumim.main.enviar_mensagem_texto")
def test_duas_imagens_do_mesmo_numero_nao_duplicam_o_perfil(mock_enviar, db_session_factory):
    main_module.registrar_tentativa_imagem("5591999999999", {"image": {"id": "1", "caption": "foto 1"}})
    main_module.registrar_tentativa_imagem("5591999999999", {"image": {"id": "2", "caption": "foto 2"}})

    with db_session_factory() as session:
        alunos = session.query(LearnerProfile).filter_by(phone_number="5591999999999").all()
        assert len(alunos) == 1

        mensagens = session.query(ChatMessage).filter_by(learner_id=alunos[0].id).all()
        assert len(mensagens) == 4  # 2 tentativas x (user + assistant)
