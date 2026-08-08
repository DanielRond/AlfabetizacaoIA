'use strict';

const { buildClient } = require('./session');
const { handleInboundMessage } = require('./handlers');
const { checkHealth } = require('./apiClient');
const { limparMediaAntiga } = require('./media');
const { childLogger } = require('./logger');
const config = require('./config');

const log = childLogger();

const BASE_RECONNECT_MS = 5000;
const MAX_RECONNECT_MS = 60000;
const MAX_RECONNECT_ATTEMPTS = 10;

let client = null;
let restartTimer = null;
let attempts = 0;
let shuttingDown = false;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function scheduleRestart(reason) {
  if (shuttingDown || restartTimer) {
    return;
  }

  attempts += 1;
  const delay = Math.min(BASE_RECONNECT_MS * 2 ** (attempts - 1), MAX_RECONNECT_MS);
  log.warn({ reason, attempts, delay }, 'Sessão desconectada. Reconectando em alguns segundos...');

  restartTimer = setTimeout(() => {
    restartTimer = null;
    start().catch((err) => {
      log.error({ err: err.message }, 'Falha na reconexão.');
      if (attempts >= MAX_RECONNECT_ATTEMPTS) {
        log.fatal('Muitas tentativas de reconexão. Encerrando o conector.');
        process.exit(1);
      }
    });
  }, delay);
}

async function start() {
  if (shuttingDown) {
    return;
  }

  try {
    const removidos = await limparMediaAntiga(config.mediaDir, config.mediaRetentionMs);
    if (removidos > 0) {
      log.info({ removidos }, 'Mídia antiga removida do diretório de entrada.');
    }
  } catch (err) {
    log.warn({ err: err.message }, 'Falha na limpeza de mídia antiga.');
  }

  client = buildClient(handleInboundMessage);

  client.on('disconnected', (reason) => {
    log.warn({ reason }, 'Conexão com o WhatsApp encerrada.');
    client.destroy().catch(() => {});
    scheduleRestart(reason);
  });

  await client.initialize();
  attempts = 0;
}

async function main() {
  const health = await checkHealth();
  if (health && health.status === 'healthy') {
    log.info({ service: health.service }, 'Backend Python saudável.');
  } else {
    log.warn('Backend Python não respondeu em /health. O conector continuará e fará retry por mensagem.');
  }

  await start();
  log.info('Conector WhatsApp iniciado. Pressione Ctrl+C para encerrar.');
}

async function shutdown() {
  shuttingDown = true;
  log.info('Encerrando o conector WhatsApp...');
  if (restartTimer) {
    clearTimeout(restartTimer);
    restartTimer = null;
  }
  if (client) {
    try {
      await client.destroy();
    } catch {
      // sessão já encerrada
    }
  }
  process.exit(0);
}

process.on('SIGINT', () => {
  shutdown().catch(() => process.exit(1));
});
process.on('SIGTERM', () => {
  shutdown().catch(() => process.exit(1));
});

main().catch((err) => {
  log.error({ err: err.message }, 'Falha fatal na inicialização.');
  process.exit(1);
});
