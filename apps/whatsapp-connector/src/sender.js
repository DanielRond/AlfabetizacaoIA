'use strict';

const fs = require('fs/promises');
const path = require('path');
const { resolveMediaRef } = require('./media');
const config = require('./config');

async function sendText(client, target, text) {
  await client.sendMessage(target, text);
}

async function sendAudio(client, target, mediaRef, opts = {}) {
  const {
    mediaBaseDir = config.mediaBaseDir,
    MessageMediaCtor = require('whatsapp-web.js').MessageMedia,
    readFile = fs.readFile,
  } = opts;

  const filePath = resolveMediaRef(mediaBaseDir, mediaRef);
  const buffer = await readFile(filePath);
  const media = new MessageMediaCtor('audio/ogg', buffer.toString('base64'), path.basename(filePath));
  await client.sendMediaAsVoice(target, media);
}

// A action vinda do backend Python é a fonte da verdade para o envio.
async function dispatchResponse(client, target, response, opts = {}) {
  const action = response && response.action ? response.action : 'noop';

  switch (action) {
    case 'send_text':
      if (response.text) {
        await sendText(client, target, response.text);
      }
      break;
    case 'send_audio':
      if (response.media_ref) {
        await sendAudio(client, target, response.media_ref, opts);
      }
      break;
    case 'request_retry':
      if (response.text) {
        await sendText(client, target, response.text);
      }
      break;
    case 'noop':
    default:
      break;
  }

  return action;
}

module.exports = { dispatchResponse, sendText, sendAudio };
