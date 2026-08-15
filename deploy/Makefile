# =====================================================================
# Makefile de deploy — Curumim Marajoara (Docker Compose)
#
# Uso: rodar de dentro de deploy/ ou via `make -C deploy <target>`.
# Pré-requisitos: Docker + plugin compose (docker compose).
#
# ATENÇÃO: copie deploy/.env.compose.example para deploy/.env antes de
# subir (o compose lê env_file: .env relativo ao deploy/).
# =====================================================================

# O compose.yaml vive ao lado deste Makefile (deploy/), então os
# comandos rodam com o diretório atual já sendo deploy/.
COMPOSE := docker compose -f compose.yaml

# Padrão: sobe backend + connector sem o Ollama
.DEFAULT_GOAL := up

# Constrói as imagens (backend é pesado: torch/nemo; só o necessário)
build:
	$(COMPOSE) build

# Sobe backend + connector em segundo plano.
# --remove-orphans: limpa containers de perfis/composes antigos.
up:
	$(COMPOSE) up -d --remove-orphans

# Igual ao up, mas ATIVA o perfil "ollama" (IA local no compose).
# Útil em VPS/desktop sem Gemini: puxe o modelo antes com
# `ollama pull llama3.2` (a porta 127.0.0.1:11434 fica exposta p/ isso).
up-ollama:
	$(COMPOSE) --profile ollama up -d --remove-orphans

# Derruba os containers. Os volumes NOMEADOS são preservados
# (banco, sessão WhatsApp, modelos do Ollama).
down:
	$(COMPOSE) down

# Logs de todos os serviços (stdout do Docker = pino JSON / Loguru)
logs:
	$(COMPOSE) logs -f --tail=100

# Status dos serviços
ps:
	$(COMPOSE) ps

# Smoke test: health check do backend (precisa da porta 127.0.0.1:5000)
smoke:
	curl -sf http://127.0.0.1:5000/health && echo "backend OK"

# Mostra o QR code do WhatsApp na 1ª execução (Ctrl+C para sair).
# O qrcode-terminal imprime o QR no stdout do connector.
qr:
	$(COMPOSE) logs -f connector | grep -iE "qr|scan"

.PHONY: build up up-ollama down logs ps smoke qr
