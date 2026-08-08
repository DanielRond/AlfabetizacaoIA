'use strict';

// Testes de contrato Node <-> Python: validam o payload do conector contra as
// fixtures JSON do contrato em specs/002-whatsappjs-python-split/contracts/fixtures/.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { normalizeMessage } = require('../src/normalizer');

const FIXTURES_DIR = path.resolve(__dirname, '../../../specs/002-whatsappjs-python-split/contracts/fixtures');

function loadFixture(name) {
  return JSON.parse(fs.readFileSync(path.join(FIXTURES_DIR, name), 'utf8'));
}

test('inbound-message fixture é normalizada pelo conector sem perda de campos', () => {
  const fixture = loadFixture('inbound-message.json');
  const message = {
    from: fixture.metadata.chat_id,
    fromMe: false,
    body: fixture.text,
    type: 'chat',
    hasMedia: false,
    id: { id: fixture.message_id },
    timestamp: Date.now() / 1000,
  };

  const normalized = normalizeMessage(message);

  assert.equal(normalized.message_id, fixture.message_id);
  assert.equal(normalized.phone_number, fixture.phone_number);
  assert.equal(normalized.message_type, 'text');
  assert.equal(normalized.text, fixture.text);
  assert.equal(normalized.needsMedia, false);
  assert.equal(normalized.metadata.chat_id, fixture.metadata.chat_id);
});

test('fixtures do contrato mantêm os campos obrigatórios do envelope', () => {
  const inbound = loadFixture('inbound-message.json');
  for (const field of ['correlation_id', 'message_id', 'phone_number', 'message_type', 'text']) {
    assert.ok(inbound[field] !== undefined && inbound[field] !== null, `faltou campo ${field}`);
  }

  const delivered = loadFixture('delivered.json');
  for (const field of ['correlation_id', 'message_id', 'phone_number', 'action', 'status', 'delivered_at']) {
    assert.ok(delivered[field] !== undefined && delivered[field] !== null, `faltou campo ${field}`);
  }
  assert.ok(['delivered', 'failed'].includes(delivered.status), 'status deve ser delivered|failed');
});
