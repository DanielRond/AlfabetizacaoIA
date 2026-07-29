from curumim.services.ai_service import gerar_resposta_ia

pergunta = "O que são os búfalos na ilha do Marajó?"
print(f"Pergunta: {pergunta}")

# Isso vai disparar o RAG + a chamada ao Ollama
resposta = gerar_resposta_ia(pergunta, nivel_pedagogico="iniciante")

print(f"\nResposta da IA:\n{resposta}")