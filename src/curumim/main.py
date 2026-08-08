"""
Curumim Backend - Processamento de IA, Transcrição e RAG
======================================================
Servidor Flask que implementa a API interna de processamento, recebendo
mensagens normalizadas do conector Node.js e retornando instruções estruturadas.
"""

import os
import json
from typing import Tuple
from datetime import datetime, timezone
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from curumim.logger_config import logger

# Importações internas
from curumim.models.database import SessionLocal, LearnerProfile, ChatMessage, MediaArtifact, InteractionRecord, inicializar_banco
from curumim.services.ai_service import gerar_resposta_ia
from curumim.services.stt_service import transcrever_audio
from curumim.services.tts_service import sintetizar_fala, tts_disponivel

load_dotenv()


def create_app() -> Flask:
    """Fábrica de Aplicação: Cria e configura o Flask para o backend Curumim."""
    app_instance = Flask(__name__)

    # Inicialização do Banco de Dados
    with app_instance.app_context():
        inicializar_banco()
        logger.info("Banco de dados verificado e tabelas criadas.")

    # Registro das rotas da API interna (Contrato Node <-> Python)
    app_instance.add_url_rule('/v1/messages/inbound', 'handle_inbound_message', handle_inbound_message, methods=['POST'])
    app_instance.add_url_rule('/v1/messages/delivered', 'handle_message_delivered', handle_message_delivered, methods=['POST'])
    app_instance.add_url_rule('/health', 'health_check', health_check, methods=['GET'])
    app_instance.add_url_rule('/v1/health', 'health_check_v1', health_check, methods=['GET'])

    return app_instance


# --- ROTAS DA API INTERNA ---

def health_check() -> Tuple[Response, int]:
    """Endpoint de saúde para validação de inicialização pelo Node.js."""
    return jsonify({
        "status": "healthy",
        "service": "curumim-backend-python",
        "version": "1.0.0"
    }), 200


def handle_inbound_message() -> Tuple[Response, int]:
    """
    Endpoint principal (POST /v1/messages/inbound).
    Recebe mensagens normalizadas do conector Node.js, processa perfil, 
    transcrição (se áudio), IA/RAG e retorna um ProcessingResult.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "correlation_id": None,
            "action": "error",
            "text": "Payload JSON ausente ou malformado.",
            "media_ref": None,
            "media_type": None,
            "status": "error",
            "error_code": "INVALID_JSON_PAYLOAD"
        }), 400

    correlation_id = data.get("correlation_id")
    message_id = data.get("message_id")
    phone_number = data.get("phone_number")
    message_type = data.get("message_type")
    text = data.get("text", "")
    media_ref = data.get("media_ref")

    # Validação de campos obrigatórios
    if not phone_number or not correlation_id:
        return jsonify({
            "correlation_id": correlation_id,
            "action": "error",
            "text": "Campos obrigatórios ausentes (phone_number ou correlation_id).",
            "media_ref": None,
            "media_type": None,
            "status": "error",
            "error_code": "MISSING_REQUIRED_FIELDS"
        }), 400

    logger.info(f"[Inbound] MsgID: {message_id} | Correlação: {correlation_id} | De: {phone_number} | Tipo: {message_type}")

    try:
        texto_processado = text
        veio_como_audio = False

        # 1. Tratamento de Áudio: Se veio áudio, transcrevemos usando o caminho local (media_ref) salvo pelo Node
        if message_type == 'audio':
            veio_como_audio = True
            if media_ref and os.path.exists(media_ref):
                try:
                    texto_processado = transcrever_audio(media_ref)
                except Exception as e:
                    logger.error(f"Erro ao transcrever áudio em {media_ref}: {e}")
                    return jsonify({
                        "correlation_id": correlation_id,
                        "action": "request_retry",
                        "text": "Desculpe, não consegui entender o áudio. Pode repetir?",
                        "media_ref": None,
                        "media_type": None,
                        "status": "retry",
                        "error_code": "AUDIO_TRANSCRIPTION_FAILED"
                    }), 200
            else:
                return jsonify({
                    "correlation_id": correlation_id,
                    "action": "request_retry",
                    "text": "Arquivo de áudio não encontrado no servidor.",
                    "media_ref": None,
                    "media_type": None,
                    "status": "retry",
                    "error_code": "MEDIA_FILE_NOT_FOUND"
                }), 200

        # 2. Tratamento de Imagem ou outros tipos não suportados
        elif message_type == 'image':
            texto_processado = "[imagem enviada]"
            resposta_recusa = "Poxa, eu não consigo ver sua imagem, consegue digitar ou mandar um áudio do que quer dizer?"
            _salvar_interacao_banco(phone_number, texto_processado, resposta_recusa, 'image')
            
            return jsonify({
                "correlation_id": correlation_id,
                "action": "send_text",
                "text": resposta_recusa,
                "media_ref": None,
                "media_type": None,
                "status": "ok",
                "error_code": None
            }), 200

        if not texto_processado or not texto_processado.strip():
            return jsonify({
                "correlation_id": correlation_id,
                "action": "noop",
                "text": "",
                "media_ref": None,
                "media_type": None,
                "status": "ok",
                "error_code": None
            }), 200

        # 3. Processamento de Perfil, Onboarding, Histórico e IA Pedagógica
        resposta_ia, nivel_aluno, em_onboarding = _processar_negocio_ia(phone_number, texto_processado, veio_como_audio)

        # 4. Construção do Artefato de Áudio (TTS) se aplicável
        action = "send_text"
        audio_artifact_ref = None
        media_type = None

        if not em_onboarding and tts_disponivel() and deve_incluir_audio(nivel_aluno, veio_como_audio):
            try:
                caminho_tts = sintetizar_fala(resposta_ia)
                if caminho_tts and os.path.exists(caminho_tts):
                    action = "send_audio"
                    audio_artifact_ref = caminho_tts
                    media_type = "audio"
                    _registrar_artefato_audio(phone_number, caminho_tts)
            except Exception as e:
                logger.error(f"Erro ao sintetizar áudio de resposta para {phone_number}: {e}")

        _registrar_interacao(phone_number, correlation_id, data, resposta_ia, action)

        # 5. Retorno do ProcessingResult estruturado para o Node.js
        return jsonify({
            "correlation_id": correlation_id,
            "action": action,
            "text": resposta_ia,
            "media_ref": audio_artifact_ref,
            "media_type": media_type,
            "status": "ok",
            "error_code": None
        }), 200

    except Exception as e:
        logger.error(f"[Inbound] Erro interno ao processar mensagem para {phone_number}: {e}")
        return jsonify({
            "correlation_id": correlation_id,
            "action": "error",
            "text": "Erro interno no servidor ao processar a mensagem.",
            "media_ref": None,
            "media_type": None,
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR"
        }), 500


def handle_message_delivered() -> Tuple[Response, int]:
    """
    Endpoint de confirmação de entrega (POST /v1/messages/delivered).
    O Node confirma se a resposta (texto/áudio) foi entregue ou falhou.
    """
    data = request.get_json(silent=True) or {}
    correlation_id = data.get("correlation_id")
    status = data.get("status")  # 'delivered' | 'failed'
    action = data.get("action")
    media_ref = data.get("media_ref")

    if not correlation_id or status not in ("delivered", "failed"):
        logger.warning(f"[Delivered] Payload inválido recebido: {data}")
        return jsonify({"status": "error"}), 400

    logger.info(f"[Delivered] Correlação: {correlation_id} | Status: {status} | Action: {action}")

    try:
        with SessionLocal() as session:
            perfil = None
            interacao = session.query(InteractionRecord).filter_by(correlation_id=correlation_id).first()
            if interacao:
                perfil = session.query(LearnerProfile).filter_by(id=interacao.profile_id).first()

            if perfil is None and data.get("phone_number"):
                perfil = session.query(LearnerProfile).filter_by(phone_number=data.get("phone_number")).first()

            if perfil is None:
                return jsonify({"status": "ok"}), 200

            novo_status = 'sent' if status == 'delivered' else 'failed'
            session.add(InteractionRecord(
                profile_id=perfil.id,
                correlation_id=correlation_id,
                direction='outbound',
                payload_snapshot=json.dumps(data, ensure_ascii=False),
                response_text=data.get("error") or data.get("text") or "",
                status=novo_status,
            ))

            if action == 'send_audio' and media_ref:
                artefato = (
                    session.query(MediaArtifact)
                    .filter_by(profile_id=perfil.id, local_path=media_ref)
                    .order_by(MediaArtifact.id.desc())
                    .first()
                )
                if artefato:
                    artefato.status = novo_status

            session.commit()
    except Exception as e:
        logger.error(f"[Delivered] Erro ao registrar entrega: {e}")

    return jsonify({"status": "ok"}), 200


# --- REGRAS DE NEGÓCIO E AUXILIARES ---

def _processar_negocio_ia(numero: str, texto: str, veio_como_audio: bool) -> Tuple[str, str, bool]:
    """Gerencia o perfil do aluno, o onboarding, o histórico e aciona a IA."""
    with SessionLocal() as session:
        aluno = session.query(LearnerProfile).filter_by(phone_number=numero).first()
        if not aluno:
            aluno = LearnerProfile(phone_number=numero, pedagogical_level='iniciante', onboarding_state='new')
            session.add(aluno)
            session.commit()

        aluno.last_seen_at = datetime.now(timezone.utc)

        tipo_msg = 'audio' if veio_como_audio else 'text'

        # Salva mensagem recebida do usuário
        session.add(ChatMessage(
            learner_id=aluno.id,
            sender='user',
            content=texto,
            message_type=tipo_msg
        ))
        session.commit()

        em_onboarding = False
        resposta = None

        if aluno.onboarding_state == 'new':
            em_onboarding = True
            resposta = (
                "Oi! Eu sou a Curumim, sua professora de alfabetização com contexto marajoara. "
                "Para eu te ajudar melhor, me diga: você é iniciante, básico ou intermediário?"
            )
            aluno.onboarding_state = 'collecting_level'
        elif aluno.onboarding_state == 'collecting_level':
            em_onboarding = True
            nivel_escolhido = _interpretar_nivel(texto)
            if nivel_escolhido:
                aluno.pedagogical_level = nivel_escolhido
                aluno.onboarding_state = 'active'
                resposta = f"Perfeito! Registrei seu nível como {nivel_escolhido}. Vamos aprender juntos!"
            else:
                resposta = (
                    "Não entendi. Por favor, escolha um destes níveis: "
                    "iniciante, básico ou intermediário."
                )

        session.add(aluno)
        session.commit()

        if not em_onboarding:
            resposta = gerar_resposta_ia(texto, aluno.pedagogical_level)

        # Salva resposta do assistente
        session.add(ChatMessage(
            learner_id=aluno.id,
            sender='assistant',
            content=resposta,
            message_type='text'
        ))
        session.commit()

        return resposta, aluno.pedagogical_level, em_onboarding


def _interpretar_nivel(texto: str) -> str | None:
    """Mapeia a resposta do aluno para um nível pedagógico válido."""
    t = texto.lower()
    for origem, destino in (('ç', 'c'), ('é', 'e'), ('á', 'a'), ('í', 'i'), ('ó', 'o'), ('ú', 'u')):
        t = t.replace(origem, destino)
    if any(palavra in t for palavra in ("intermediario", "avancado", "medio")):
        return 'intermediario'
    if "basico" in t:
        return 'basico'
    if any(palavra in t for palavra in ("iniciante", "iniciando", "novo", "new")):
        return 'iniciante'
    return None


def _salvar_interacao_banco(numero: str, texto_usuario: str, resposta: str, tipo_msg: str):
    """Salva interações especiais (ex: imagens) no banco."""
    with SessionLocal() as session:
        try:
            aluno = session.query(LearnerProfile).filter_by(phone_number=numero).first()
            if not aluno:
                aluno = LearnerProfile(phone_number=numero, pedagogical_level='iniciante')
                session.add(aluno)
                session.commit()

            session.add(ChatMessage(
                learner_id=aluno.id,
                sender='user',
                content=texto_usuario,
                message_type=tipo_msg
            ))
            session.add(ChatMessage(
                learner_id=aluno.id,
                sender='assistant',
                content=resposta,
                message_type='text'
            ))
            session.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar interação especial no banco: {e}")
            session.rollback()


def deve_incluir_audio(nivel_pedagogico: str, veio_como_audio: bool) -> bool:
    """Define se a resposta deve ser convertida em áudio com base no nível do aluno."""
    if nivel_pedagogico in ("new", "iniciante"):
        return True  # reforço de áudio para quem mais precisa
    if nivel_pedagogico == "basico":
        return veio_como_audio  # mantém o formato que o aluno usou
    return False  # intermediário+ foca em texto


def _registrar_interacao(numero: str, correlation_id: str, payload: dict, resposta: str, action: str):
    """Registra um InteractionRecord de entrada para rastreio ponta a ponta."""
    try:
        with SessionLocal() as session:
            aluno = session.query(LearnerProfile).filter_by(phone_number=numero).first()
            if aluno is None:
                return
            session.add(InteractionRecord(
                profile_id=aluno.id,
                correlation_id=correlation_id,
                direction='inbound',
                payload_snapshot=json.dumps(payload, ensure_ascii=False, default=str),
                response_text=resposta,
                status='processed' if action != 'error' else 'failed',
            ))
            session.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar InteractionRecord para {numero}: {e}")


def _registrar_artefato_audio(numero: str, caminho: str):
    """Registra um MediaArtifact 'ready' para um áudio TTS gerado pelo backend."""
    try:
        with SessionLocal() as session:
            aluno = session.query(LearnerProfile).filter_by(phone_number=numero).first()
            if aluno is None:
                return
            session.add(MediaArtifact(
                profile_id=aluno.id,
                artifact_type='audio',
                local_path=caminho,
                mime_type='audio/ogg',
                status='ready',
            ))
            session.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar MediaArtifact para {numero}: {e}")


# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    flask_app = create_app()
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Iniciando o backend Python Flask na porta {port}...")
    flask_app.run(host="0.0.0.0", port=port, debug=True)