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

module.exports = { saveInboundMedia, resolveMediaRef, safeFilename, ensureDir };
