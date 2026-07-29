from curumim.services.rag_service import buscar_contexto  # <- Ajuste o nome aqui

pergunta = "O que é o Marajó?"
contexto = buscar_contexto(pergunta)  # <- Ajuste o nome aqui

print("--- CONTEXTO RECUPERADO DO CHROMA ---")
print(contexto)