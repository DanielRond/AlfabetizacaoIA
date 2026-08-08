'use strict';

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const config = require('./config');
const { childLogger } = require('./logger');

function printQr(qr) {
  qrcode.generate(qr, { small: true });
}

function buildClient(onMessage) {
  const log = childLogger();

  const puppeteer = {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  };

  if (config.browserPath) {
    puppeteer.executablePath = config.browserPath;
  }

  const client = new Client({
    authStrategy: new LocalAuth({ dataPath: config.sessionDir }),
    puppeteer,
  });

  client.on('qr', (qr) => {
    log.info('QR gerado. Escaneie com o WhatsApp conectado ao telefone.');
    printQr(qr);
  });

  client.on('authenticated', () => {
    log.info('Sessão autenticada no WhatsApp.');
  });

  client.on('auth_failure', (msg) => {
    log.warn({ msg }, 'Falha de autenticação no WhatsApp.');
  });

  client.on('ready', () => {
    log.info('Conector WhatsApp pronto para receber mensagens.');
  });

  client.on('change_state', (state) => {
    log.debug({ state }, 'Estado da sessão WhatsApp alterado.');
  });

  client.on('message', (message) => {
    Promise.resolve(onMessage(client, message)).catch((err) => {
      log.error(
        { err: err.message, message_id: message.id && message.id.id },
        'Erro não tratado ao processar mensagem.'
      );
    });
  });

  return client;
}

module.exports = { buildClient };
