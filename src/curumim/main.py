import os
import threading
from typing import Any, Tuple, Union
from flask import Flask, request, jsonify, make_response, Response
from dotenv import load_dotenv
from curumim.logger_config import logger

# Importações internas
from curumim.models.database import SessionLocal, LearnerProfile, ChatMessage, inicializar_banco
from curumim.services.whatsapp_service import enviar_mensagem_texto, enviar_mensagem_audio
from curumim.services.ai_service import gerar_resposta_ia
from curumim.services.voice_service import baixar_audio, transcrever_audio
from curumim.services.tts_service import sintetizar_fala, tts_disponivel

load_dotenv()


def create_app() -> Flask:
    """Fábrica de Aplicação: Cria e configura o Flask."""
    app_instance = Flask(__name__)

    # Inicialização do Banco
    with app_instance.app_context():
        inicializar_banco()
        logger.info("Banco de dados verificado e tabelas criadas.")

    # Registro das rotas
    app_instance.add_url_rule('/webhook', 'verificar_webhook', verificar_webhook, methods=['GET'])
    app_instance.add_url_rule('/webhook', 'receber_mensagem', receber_mensagem, methods=['POST'])

    return app_instance


# --- ROTAS ---

def verificar_webhook() -> Union[Response, Tuple[Response, int]]:
    """Valida o webhook junto à Meta."""
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")

    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return make_response(str(challenge), 200)

    return make_response("Token inválido", 403)


def receber_mensagem() -> Tuple[Response, int]:
    """Recebe o POST da Meta e distribui as mensagens para processamento."""
    dados = request.json
    if not dados or 'entry' not in dados:
        return jsonify({"status": "recebido"}), 200

    for msg_info in _extrair_mensagens(dados):
        threading.Thread(target=processar_mensagem_whatsapp, args=(msg_info,)).start()

    return jsonify({"status": "recebido"}), 200


# --- UTILITÁRIOS ---

def _extrair_mensagens(dados: Any):
    """Achata a estrutura aninhada do JSON da Meta."""
    if not isinstance(dados, dict):
        return

    for entry in dados.get('entry', []):
        for change in entry.get('changes', []):
            yield from change.get('value', {}).get('messages', [])


# --- LÓGICA DE NORMALIZAÇÃO ---

def processar_mensagem_whatsapp(mensagem_info: dict[str, Any]):
    """Orquestra a extração do texto da mensagem e repassa para a regra de negócio."""
    numero = str(mensagem_info.get('from') or "")
    tipo_msg = str(mensagem_info.get('type') or "")
    texto = ""

    if tipo_msg == 'text':
        texto = mensagem_info.get('text', {}).get('body', '')
    elif tipo_msg == 'audio':
        texto = extrair_texto_de_audio(mensagem_info, numero)

    if not texto.strip():
        return

    processar_interacao_aluno(numero, texto, veio_como_audio=(tipo_msg == 'audio'))


def extrair_texto_de_audio(mensagem_info: dict[str, Any], numero: str) -> str:
    """Isola a lógica de download, transcrição e limpeza de arquivos de áudio."""
    audio_node = mensagem_info.get('audio')

    if not isinstance(audio_node, dict):
        return ""

    media_id = audio_node.get('id')
    if not isinstance(media_id, str):
        return ""

    try:
        caminho = baixar_audio(media_id)
        texto = transcrever_audio(caminho)

        if os.path.exists(caminho):
            os.remove(caminho)

        return texto
    except Exception as e:
        logger.error(f"Erro ao transcrever áudio de {numero}: {e}")
        enviar_mensagem_texto(numero, "Desculpe, não consegui entender o áudio. Pode repetir?")
        return ""


# --- REGRA DE NEGÓCIO ---

def processar_interacao_aluno(numero: str, texto: str, veio_como_audio: bool = False):
    """Gerencia o acesso ao banco de dados, salva o histórico e comunica com a IA."""
    resposta = None
    nivel = 'iniciante'

    with SessionLocal() as session:
        try:
            # 1. Busca ou cria o perfil do aluno
            aluno = session.query(LearnerProfile).filter_by(phone_number=numero).first()
            if not aluno:
                aluno = LearnerProfile(phone_number=numero, pedagogical_level='iniciante')
                session.add(aluno)
                session.commit()

            nivel = aluno.pedagogical_level

            # 2. Salva a mensagem recebida do aluno no banco de dados
            msg_aluno = ChatMessage(
                learner_id=aluno.id,
                sender='user',
                content=texto,
                message_type='audio' if veio_como_audio else 'text'
            )
            session.add(msg_aluno)
            session.commit()

            # 3. Gera a resposta da IA (Curumim)
            resposta = gerar_resposta_ia(texto, nivel)

            # 4. Salva a resposta gerada pela IA no banco de dados
            msg_ia = ChatMessage(
                learner_id=aluno.id,
                sender='assistant',
                content=resposta,
                message_type='text'
            )
            session.add(msg_ia)
            session.commit()

            # 5. Envia a resposta de volta para o WhatsApp do aluno
            enviar_mensagem_texto(numero, resposta)

        except Exception as e:
            logger.error(f"Erro na regra de negócio para {numero}: {e}")
            session.rollback()
            return

    if resposta and tts_disponivel() and deve_incluir_audio(nivel, veio_como_audio):
        _responder_com_audio(numero, resposta)


def _responder_com_audio(numero: str, resposta: str):
    caminho_audio = None
    try:
        caminho_audio = sintetizar_fala(resposta)
        if caminho_audio:
            enviar_mensagem_audio(numero, caminho_audio)
    except Exception as e:
        logger.error(f"Erro ao gerar/enviar áudio de resposta para {numero}: {e}")
    finally:
        if caminho_audio and os.path.exists(caminho_audio):
            os.remove(caminho_audio)


# TODO: Implementar lógica de atualização do nível pedagógico do aluno com base nas interações e respostas da IA. Esse formato é só um ponto de partida.
def deve_incluir_audio(nivel_pedagogico: str, veio_como_audio: bool) -> bool:
    if nivel_pedagogico in ("new", "iniciante"):
        return True  # reforço máximo de áudio pra quem mais precisa
    if nivel_pedagogico == "basico":
        return veio_como_audio  # mantém o formato que o aluno já usa
    return False  # intermediario+: só texto, a IA já domina a leitura


# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    flask_app = create_app()
    logger.info("Iniciando o servidor Flask de desenvolvimento na porta 5000...")
    flask_app.run(port=5000)
