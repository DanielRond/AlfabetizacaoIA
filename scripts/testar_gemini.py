import os
from dotenv import load_dotenv
from curumim.services.ai_service import gerar_resposta_ia

# ISSO É O MAIS IMPORTANTE:
load_dotenv()

# Verifique se o provedor está carregando
print(f"Provedor carregado do .env: {os.getenv('IA_PROVIDER')}")

resposta = gerar_resposta_ia("O que são os búfalos na ilha do Marajó?")
print(f"Resposta: {resposta}")

# Carrega as variáveis do .env
load_dotenv()

# Define o provedor para o teste
os.environ["IA_PROVIDER"] = "gemini"

print("--- Testando conexão com Gemini ---")
try:
    resposta = gerar_resposta_ia("O que são os búfalos na ilha do Marajó?")
    print(f"\nResposta da IA:\n{resposta}")
except Exception as e:
    print(f"\nErro no teste: {e}")