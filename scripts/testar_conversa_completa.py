from curumim.services.ai_service import gerar_resposta_ia
from curumim.services.tts_service import sintetizar_fala, tts_disponivel

pergunta = "O que é a lenda da Cobra Grande?"
nivel = "iniciante"

print(f"Pergunta: {pergunta}")
resposta = gerar_resposta_ia(pergunta, nivel_pedagogico=nivel)
print(f"\nResposta da IA:\n{resposta}")

print(f"\nTTS disponível: {tts_disponivel()}")
caminho_audio = sintetizar_fala(resposta)
print(f"Áudio gerado em: {caminho_audio}")
