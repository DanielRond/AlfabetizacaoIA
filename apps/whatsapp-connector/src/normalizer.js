'use strict';

const { randomUUID } = require('crypto');

// Tipos do contrato interno: text | audio | interactive | system
const TYPE_TEXT = ['text', 'chat'];
const TYPE_AUDIO = ['audio', 'ptt'];
const TYPE_INTERACTIVE = ['button', 'interactive', 'list_response', 'template', 'list'];
const TYPE_SYSTEM = ['call_log', 'vcard', 'location', 'revoked'];
// Não suportado pelo backend: o Python devolve recusa amigável com action send_text.
const TYPE_IMAGE = ['image', 'video', 'document', 'sticker'];
const IGNORED_TYPES = ['protocol', 'e2e_notification'];

function toDigits(value) {
  if (!value) return '';
  return String(value).split('@')[0].replace(/\D/g, '');
}

function classifyMessageType(type) {
  if (TYPE_TEXT.includes(type)) return 'text';
  if (TYPE_AUDIO.includes(type)) return 'audio';
  if (TYPE_INTERACTIVE.includes(type)) return 'interactive';
  if (TYPE_IMAGE.includes(type)) return 'image';
  return 'system';
}

function extractInteractiveText(message) {
  const data = message._data || {};
  return message.selectedDisplayText || data.selectedDisplayText || message.body || '';
}

function isStatusMessage(message) {
  return Boolean(message.isStatus) || message.from === 'status@broadcast';
}

function normalizeMessage(message) {
  if (!message || message.fromMe) return null;
  if (IGNORED_TYPES.includes(message.type)) return null;
  if (isStatusMessage(message)) return null;

  const messageType = classifyMessageType(message.type);
  const rawText = messageType === 'interactive' ? extractInteractiveText(message) : message.body || '';

  const normalized = {
    message_id: message.id && message.id.id ? String(message.id.id) : null,
    phone_number: toDigits(message.author || message.from),
    message_type: messageType,
    text: message.hasMedia ? '' : rawText.trim(),
    media_ref: null,
    received_at: message.timestamp
      ? new Date(message.timestamp * 1000).toISOString()
      : new Date().toISOString(),
    metadata: {
      chat_id: message.from || null,
      from_me: Boolean(message.fromMe),
    },
    needsMedia: Boolean(message.hasMedia),
  };

  if (messageType === 'text' && normalized.text.length === 0) {
    // Mensagem vazia sem mídia: não há o que processar.
    normalized.message_type = 'system';
  }

  return normalized;
}

module.exports = { normalizeMessage, classifyMessageType, toDigits };
