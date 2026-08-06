'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs/promises');
const os = require('os');
const path = require('path');
const { dispatchResponse, sendText, sendAudio } = require('../src/sender');

function makeClient() {
  const sent = [];
  return {
    sent,
    async sendMessage(target, text) {
      sent.push({ kind: 'text', target, text });
    },
    async sendMediaAsVoice(target, media) {
      sent.push({ kind: 'voice', target, media });
    },
  };
}

class FakeMedia {
  constructor(mimetype, data, filename) {
    this.mimetype = mimetype;
    this.data = data;
    this.filename = filename;
  }
}

let tmpDir;
let audioPath;

test.before(async () => {
  tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'connector-sender-'));
  audioPath = path.join(tmpDir, 'resposta.ogg');
  await fs.writeFile(audioPath, Buffer.from('conteudo-de-audio'));
});

test.after(async () => {
  await fs.rm(tmpDir, { recursive: true, force: true });
});

test('sendText envia o texto para o destino', async () => {
  const client = makeClient();
  await sendText(client, '5511999999999@c.us', 'ola aluno');
  assert.equal(client.sent.length, 1);
  assert.equal(client.sent[0].kind, 'text');
  assert.equal(client.sent[0].target, '5511999999999@c.us');
  assert.equal(client.sent[0].text, 'ola aluno');
});

test('sendAudio envia como voz a partir do media_ref', async () => {
  const client = makeClient();
  await sendAudio(client, '5511999999999@c.us', audioPath, {
    mediaBaseDir: tmpDir,
    MessageMediaCtor: FakeMedia,
  });

  assert.equal(client.sent.length, 1);
  const call = client.sent[0];
  assert.equal(call.kind, 'voice');
  assert.equal(call.target, '5511999999999@c.us');
  assert.equal(call.media.mimetype, 'audio/ogg');
  assert.equal(call.media.filename, 'resposta.ogg');
  assert.equal(
    Buffer.from(call.media.data, 'base64').toString(),
    'conteudo-de-audio'
  );
});

test('sendAudio resolve media_ref relativo contra a mediaBaseDir', async () => {
  const client = makeClient();
  await sendAudio(client, 'x', 'data/audios/resposta.ogg', {
    mediaBaseDir: tmpDir,
    MessageMediaCtor: FakeMedia,
    readFile: async (p) => {
      assert.equal(path.resolve(p), path.join(tmpDir, 'data', 'audios', 'resposta.ogg'));
      return Buffer.from('fake');
    },
  });
  assert.equal(client.sent.length, 1);
});

test('dispatchResponse envia texto para action send_text', async () => {
  const client = makeClient();
  const action = await dispatchResponse(client, 'c', { action: 'send_text', text: 'oi' });
  assert.equal(action, 'send_text');
  assert.equal(client.sent[0].text, 'oi');
});

test('dispatchResponse ignora send_text sem texto', async () => {
  const client = makeClient();
  await dispatchResponse(client, 'c', { action: 'send_text', text: '' });
  assert.equal(client.sent.length, 0);
});

test('dispatchResponse envia áudio para action send_audio', async () => {
  const client = makeClient();
  await dispatchResponse(client, 'c', { action: 'send_audio', media_ref: 'resposta.ogg' }, {
    mediaBaseDir: tmpDir,
    MessageMediaCtor: FakeMedia,
  });
  assert.equal(client.sent.length, 1);
  assert.equal(client.sent[0].kind, 'voice');
});

test('dispatchResponse trata request_retry como envio de texto gentil', async () => {
  const client = makeClient();
  await dispatchResponse(client, 'c', { action: 'request_retry', text: 'pode repetir?' });
  assert.equal(client.sent[0].text, 'pode repetir?');
});

test('dispatchResponse não faz nada para noop ou ausência de action', async () => {
  const client = makeClient();
  await dispatchResponse(client, 'c', { action: 'noop' });
  await dispatchResponse(client, 'c', null);
  await dispatchResponse(client, 'c', {});
  assert.equal(client.sent.length, 0);
});
