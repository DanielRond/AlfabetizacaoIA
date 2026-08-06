'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs/promises');
const os = require('os');
const path = require('path');
const { saveInboundMedia, resolveMediaRef, safeFilename } = require('../src/media');

test('safeFilename sanitiza nomes não seguros', () => {
  assert.equal(safeFilename('mensagem da criança.ogg'), 'mensagem_da_crian_a.ogg');
  assert.equal(safeFilename('ok-a_b.1.ogg'), 'ok-a_b.1.ogg');
  assert.equal(safeFilename(null), 'media');
  assert.equal(safeFilename(''), 'media');
});

test('resolveMediaRef mantém caminho absoluto como está', () => {
  const abs = path.join('C:', 'temp', 'audio.ogg');
  assert.equal(resolveMediaRef('/base', abs), abs);
});

test('resolveMediaRef junta caminho relativo à base', () => {
  const base = path.join(os.tmpdir(), 'repo');
  assert.equal(resolveMediaRef(base, 'data/audios/x.ogg'), path.join(base, 'data', 'audios', 'x.ogg'));
});

test('resolveMediaRef retorna null sem media_ref', () => {
  assert.equal(resolveMediaRef('/base', null), null);
  assert.equal(resolveMediaRef('/base', ''), null);
});

test('saveInboundMedia baixa, decodifica e salva a mídia', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'connector-media-'));
  try {
    const content = 'bytes-de-audio';
    const message = {
      async downloadMedia() {
        return {
          data: Buffer.from(content).toString('base64'),
          mimetype: 'audio/ogg; codecs=opus',
        };
      },
    };

    const filePath = await saveInboundMedia(message, dir);
    assert.ok(filePath.startsWith(dir));
    assert.match(filePath, /\.ogg$/);
    assert.equal(await fs.readFile(filePath, 'utf8'), content);
  } finally {
    await fs.rm(dir, { recursive: true, force: true });
  }
});

test('saveInboundMedia cria o diretório quando ausente', async () => {
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), 'connector-media-parent-'));
  const dir = path.join(parent, 'nested', 'media');
  try {
    const message = {
      async downloadMedia() {
        return { data: Buffer.from('x').toString('base64'), mimetype: 'image/jpeg' };
      },
    };
    const filePath = await saveInboundMedia(message, dir);
    assert.match(filePath, /\.jpeg$/);
    assert.equal(await fs.readFile(filePath, 'utf8'), 'x');
  } finally {
    await fs.rm(parent, { recursive: true, force: true });
  }
});

test('saveInboundMedia lança erro sem downloadMedia', async () => {
  await assert.rejects(() => saveInboundMedia({}, 'qualquer'), /downloadMedia/);
});

test('saveInboundMedia lança erro quando a mídia vem vazia', async () => {
  const message = { async downloadMedia() { return { data: null }; } };
  await assert.rejects(() => saveInboundMedia(message, 'qualquer'), /sem dados/);
});
