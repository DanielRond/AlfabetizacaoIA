import sys
import os
from loguru import logger

# Lê o nível de log do ambiente, padrão INFO se não definido
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Remove qualquer configuração padrão para evitar duplicidade
logger.remove()

# Configuração 1: Log no Console
# Útil para desenvolvimento (ativar com LOG_LEVEL=DEBUG no .env)
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True
)

# Configuração 2: Log em Arquivo
# Rotaciona todo dia à meia-noite e mantém o histórico por 10 dias
logger.add(
    "logs/alfabot_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="10 days",
    level="INFO",
    encoding="utf-8",
    compression="zip" # Opcional: comprime logs antigos para economizar espaço
)