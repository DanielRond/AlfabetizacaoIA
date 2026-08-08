'use strict';

const fs = require('fs/promises');
const path = require('path');
const { randomUUID } = require('crypto');

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

function safeFilename(name) {
  const base = String(name || 'media').replace(/[^a-zA-Z0-9._-]/g, '_');
  return base || 'media';
}

function extensionFromMimetype(mimetype) {
  if (!mimetype) return '.bin';
  const part = String(mimetype).split(';')[0].split('/')[1];
  return part ? `.${part}` : '.bin';
}

// Baixa a mídia da mensagem para o disco e retorna o caminho absoluto salvo.
async function saveInboundMedia(message, mediaDir) {
  if (typeof message.downloadMedia !== 'function') {
    throw new Error('Mensagem não expõe downloadMedia().');
  }
  const media = await message.downloadMedia();
  if (!media || !media.data) {
    throw new Error('downloadMedia() retornou sem dados.');
  }

  await ensureDir(mediaDir);
  const filename = `${Date.now()}_${randomUUID().slice(0, 8)}${extensionFromMimetype(media.mimetype)}`;
  const filePath = path.join(mediaDir, filename);
  await fs.writeFile(filePath, Buffer.from(media.data, 'base64'));
  return filePath;
}

// Resolve um media_ref gerado pelo backend Python contra a base compartilhada.
function resolveMediaRef(mediaBaseDir, mediaRef) {
  if (!mediaRef) return null;
  return path.isAbsolute(mediaRef) ? mediaRef : path.resolve(mediaBaseDir, mediaRef);
}

// Remove arquivos de mídia antigos do diretório (limite em ms de idade).
async function limparMediaAntiga(dir, maxAgeMs) {
  const entries = await fs.readdir(dir).catch(() => []);
  let removed = 0;
  const now = Date.now();

  for (const name of entries) {
    const filePath = path.join(dir, name);
    const st = await fs.stat(filePath).catch(() => null);
    if (st && st.isFile() && now - st.mtimeMs > maxAgeMs) {
      const ok = await fs.unlink(filePath).then(() => true).catch(() => false);
      if (ok) removed += 1;
    }
  }

  return removed;
}

module.exports = { saveInboundMedia, resolveMediaRef, safeFilename, ensureDir, limparMediaAntiga };
