import os
from loguru import logger
from curumim.services.rag_service import adicionar_conhecimento


def popular_banco():
    pasta_conhecimento = "data/knowledge"

    # Verifica se a pasta existe
    if not os.path.exists(pasta_conhecimento):
        logger.error(f"Pasta de conhecimento não encontrada: {pasta_conhecimento}")
        return

    logger.info(f"Iniciando ingestão de arquivos da pasta: {pasta_conhecimento}")

    arquivos = [f for f in os.listdir(pasta_conhecimento) if f.endswith(".txt")]

    if not arquivos:
        logger.warning("Nenhum arquivo .txt encontrado para ingestão.")
        return

    for arquivo in arquivos:
        caminho = os.path.join(pasta_conhecimento, arquivo)
        try:
            with open(caminho, 'r', encoding='utf-8-sig') as f:
                conteudo = f.read()

            # Adiciona ao ChromaDB
            adicionar_conhecimento(conteudo, id_documento=arquivo)

            logger.success(f"Documento '{arquivo}' carregado com sucesso no ChromaDB.")

        except Exception as e:
            logger.error(f"Falha ao processar o arquivo '{arquivo}': {str(e)}")

    logger.info("Processo de ingestão finalizado.")


if __name__ == "__main__":

    popular_banco()