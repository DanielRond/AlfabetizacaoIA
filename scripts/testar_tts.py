from curumim.services.tts_service import tts_disponivel, sintetizar_fala

print(f"TTS disponível: {tts_disponivel()}")

texto = "Muito bem! Você está aprendendo a ler as palavras do Marajó."
caminho = sintetizar_fala(texto)
print(f"Arquivo gerado: {caminho}")
