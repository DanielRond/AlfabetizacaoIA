'use strict';

// Testes do pipeline de mensagens (handlers.js) com dependências mockadas.
// Valida o fluxo feliz (dispatch + ack 'delivered') e o fallback em falha
// (mensagem de erro + ack 'failed').

const test = require('node:test');
const assert = require('node:assert/strict');

const LOG_STUB = { info() {}, warn() {}, error() {}, child() { return LOG_STUB; } };
const MESSAGE = {
  from: '5591999999999@c.us',
  fromMe: false,
  body: 'oi',
  type: 'chat',
  hasMedia: false,
  id: { id: 'msg-1' },
  timestamp: Date.now() / 1000,
};

function installMocks(overrides) {
  const mocks = {
    normalizeMessage: (m) => ({
      message_id: m.id.id,
      phone_number: m.from.split('@')[0],
      message_type: 'text',
      text: m.body,
      media_ref: null,
      needsMedia: false,
      metadata: { chat_id: m.from },
    }),
    saveInboundMedia: async () => '/tmp/media/audio.ogg',
    postInbound: async () => ({ action: 'send_text', text: 'Resposta' }),
    postDelivered: async () => 200,
    dispatchResponse: async () => 'send_text',
    mediaDir: '/tmp/media',
    ...overrides,
  };

  const req = require;
  const apiClientPath = req.resolve('../src/apiClient');
  const senderPath = req.resolve('../src/sender');
  const loggerPath = req.resolve('../src/logger');
  const configPath = req.resolve('../src/config');
  const normalizerPath = req.resolve('../src/normalizer');
  const mediaPath = req.resolve('../src/media');

  require.cache[apiClientPath] = {
    id: apiClientPath,
    filename: apiClientPath,
    loaded: true,
    exports: { postInbound: mocks.postInbound, postDelivered: mocks.postDelivered, checkHealth: async () => null },
  };
  require.cache[senderPath] = { id: senderPath, filename: senderPath, loaded: true, exports: { dispatchResponse: mocks.dispatchResponse } };
  require.cache[loggerPath] = { id: loggerPath, filename: loggerPath, loaded: true, exports: { childLogger: () => LOG_STUB } };
  require.cache[configPath] = { id: configPath, filename: configPath, loaded: true, exports: { mediaDir: mocks.mediaDir } };
  require.cache[normalizerPath] = { id: normalizerPath, filename: normalizerPath, loaded: true, exports: { normalizeMessage: mocks.normalizeMessage } };
  require.cache[mediaPath] = { id: mediaPath, filename: mediaPath, loaded: true, exports: { saveInboundMedia: mocks.saveInboundMedia } };

  return mocks;
}

function restore() {
  for (const name of ['../src/handlers', '../src/apiClient', '../src/sender', '../src/logger', '../src/config', '../src/normalizer', '../src/media']) {
    const resolved = require.resolve(name);
    const fresh = require.cache[resolved];
    if (fresh && fresh.children) {
      delete require.cache[resolved];
    }
  }
}

test('fluxo feliz: envia resposta e confirma entrega', async () => {
  const calls = { delivered: [] };
  const mocks = installMocks({
    postDelivered: async (payload) => { calls.delivered.push(payload); return 200; },
  });

  try {
    const { handleInboundMessage } = require('../src/handlers');
    const client = { sendMessage: async () => {} };

    const result = await handleInboundMessage(client, MESSAGE);

    assert.ok(result);
    assert.equal(result.action, 'send_text');
    assert.equal(calls.delivered.length, 1);
    assert.equal(calls.delivered[0].status, 'delivered');
    assert.equal(calls.delivered[0].message_id, 'msg-1');
    assert.equal(calls.delivered[0].phone_number, '5591999999999');
    assert.ok(calls.delivered[0].correlation_id);
  } finally {
    restore();
  }
});

test('postInbound falha: envia fallback ao aluno e ack failed', async () => {
  const calls = { sent: [], delivered: [] };
  installMocks({
    postInbound: async () => { throw new Error('backend fora'); },
    postDelivered: async (payload) => { calls.delivered.push(payload); return 200; },
  });

  try {
    const { handleInboundMessage } = require('../src/handlers');
    const client = { sendMessage: async (to, text) => { calls.sent.push(text); } };

    const result = await handleInboundMessage(client, MESSAGE);

    assert.equal(result, null);
    assert.equal(calls.sent.length, 1);
    assert.match(calls.sent[0], /probleminha/);
    assert.equal(calls.delivered.length, 1);
    assert.equal(calls.delivered[0].status, 'failed');
  } finally {
    restore();
  }
});

test('dispatchResponse falha: também cai no fallback com ack failed', async () => {
  const calls = { sent: [], delivered: [] };
  installMocks({
    dispatchResponse: async () => { throw new Error('falha no whatsapp'); },
    postDelivered: async (payload) => { calls.delivered.push(payload); return 200; },
  });

  try {
    const { handleInboundMessage } = require('../src/handlers');
    const client = { sendMessage: async (to, text) => { calls.sent.push(text); } };

    const result = await handleInboundMessage(client, MESSAGE);

    assert.equal(result, null);
    assert.equal(calls.sent.length, 1);
    assert.equal(calls.delivered.length, 1);
    assert.equal(calls.delivered[0].status, 'failed');
  } finally {
    restore();
  }
});

test('mensagem sem normalização (fromMe) é ignorada sem side effects', async () => {
  const mocks = installMocks({ normalizeMessage: () => null });

  try {
    const { handleInboundMessage } = require('../src/handlers');
    const client = { sendMessage: async () => { throw new Error('não deve enviar'); } };

    const result = await handleInboundMessage(client, { fromMe: true });

    assert.equal(result, null);
  } finally {
    restore();
  }
});
