'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { normalizeMessage, classifyMessageType, toDigits } = require('../src/normalizer');

function makeMessage(overrides = {}) {
  return {
    fromMe: false,
    type: 'text',
    body: 'ola',
    hasMedia: false,
    from: '5511999999999@c.us',
    author: null,
    timestamp: 1700000000,
    id: { id: 'ABC123', fromMe: false },
    isStatus: false,
    ...overrides,
  };
}

test('classifyMessageType mapeia os tipos do contrato', () => {
  assert.equal(classifyMessageType('text'), 'text');
  assert.equal(classifyMessageType('chat'), 'text');
  assert.equal(classifyMessageType('ptt'), 'audio');
  assert.equal(classifyMessageType('audio'), 'audio');
  assert.equal(classifyMessageType('button'), 'interactive');
  assert.equal(classifyMessageType('list_response'), 'interactive');
  assert.equal(classifyMessageType('template'), 'interactive');
  assert.equal(classifyMessageType('call_log'), 'system');
  assert.equal(classifyMessageType('vcard'), 'system');
  assert.equal(classifyMessageType('location'), 'system');
  assert.equal(classifyMessageType('image'), 'image');
  assert.equal(classifyMessageType('sticker'), 'image');
  assert.equal(classifyMessageType('desconhecido'), 'system');
});

test('toDigits extrai apenas dígitos do identificador', () => {
  assert.equal(toDigits('5511999999999@c.us'), '5511999999999');
  assert.equal(toDigits('+55 11 99999-9999'), '5511999999999');
  assert.equal(toDigits(null), '');
  assert.equal(toDigits(''), '');
});

test('mensagem de texto é normalizada com phone_number e received_at', () => {
  const msg = makeMessage({ body: '  quero aprender  ' });
  const out = normalizeMessage(msg);

  assert.equal(out.message_id, 'ABC123');
  assert.equal(out.phone_number, '5511999999999');
  assert.equal(out.message_type, 'text');
  assert.equal(out.text, 'quero aprender');
  assert.equal(out.media_ref, null);
  assert.equal(out.needsMedia, false);
  assert.equal(out.received_at, new Date(1700000000 * 1000).toISOString());
  assert.equal(out.metadata.chat_id, '5511999999999@c.us');
});

test('mensagens próprias são ignoradas', () => {
  const msg = makeMessage({ fromMe: true });
  assert.equal(normalizeMessage(msg), null);
});

test('status de broadcast é ignorado', () => {
  const msg = makeMessage({ isStatus: true });
  assert.equal(normalizeMessage(msg), null);

  const msg2 = makeMessage({ from: 'status@broadcast' });
  assert.equal(normalizeMessage(msg2), null);
});

test('tipos de protocolo são ignorados', () => {
  assert.equal(normalizeMessage(makeMessage({ type: 'protocol' })), null);
  assert.equal(normalizeMessage(makeMessage({ type: 'e2e_notification' })), null);
});

test('áudio (ptt) é classificado como audio e marcado para baixar mídia', () => {
  const msg = makeMessage({ type: 'ptt', body: '', hasMedia: true });
  const out = normalizeMessage(msg);

  assert.equal(out.message_type, 'audio');
  assert.equal(out.needsMedia, true);
  assert.equal(out.text, '');
});

test('mensagem em grupo usa o autor (message.author) como remetente', () => {
  const msg = makeMessage({
    from: '120363000000000000@g.us',
    author: '5511999999999@c.us',
    body: 'oi grupo',
  });
  const out = normalizeMessage(msg);

  assert.equal(out.phone_number, '5511999999999');
  assert.equal(out.metadata.chat_id, '120363000000000000@g.us');
});

test('resposta interativa (list_response) usa selectedDisplayText como texto', () => {
  const msg = makeMessage({
    type: 'list_response',
    body: 'escolha',
    selectedDisplayText: 'iniciante',
  });
  const out = normalizeMessage(msg);

  assert.equal(out.message_type, 'interactive');
  assert.equal(out.text, 'iniciante');
});

test('imagem vira image com needsMedia e texto vazio', () => {
  const msg = makeMessage({ type: 'image', body: '', hasMedia: true });
  const out = normalizeMessage(msg);

  assert.equal(out.message_type, 'image');
  assert.equal(out.needsMedia, true);
  assert.equal(out.text, '');
});

test('chamada (call_log) vira system', () => {
  const out = normalizeMessage(makeMessage({ type: 'call_log', body: '' }));
  assert.equal(out.message_type, 'system');
});
