'use strict';

const { randomUUID } = require('crypto');
const { normalizeMessage } = require('./normalizer');
const { saveInboundMedia } = require('./media');
const { postInbound } = require('./apiClient');
const { dispatchResponse } = require('./sender');
const { childLogger } = require('./logger');
const config = require('./config');

const FALLBACK_TEXT = 'Tive um probleminha para processar sua mensagem. Pode tentar de novo?';

async function handleInboundMessage(client, message) {
  const normalized = normalizeMessage(message);
  if (!normalized) {
    return null;
  }

  normalized.correlation_id = randomUUID();
  const log = childLogger({
    correlation_id: normalized.correlation_id,
    message_id: normalized.message_id,
    phone_number: normalized.phone_number,
  });

  log.info({ message_type: normalized.message_type }, 'Mensagem recebida do WhatsApp');

  try {
    if (normalized.needsMedia) {
      normalized.media_ref = await saveInboundMedia(message, config.mediaDir);
      log.info({ media_ref: normalized.media_ref }, 'Mídia salva para processamento');
    }

    const response = await postInbound(normalized);
    log.info(
      { action: response && response.action, status: response && response.status },
      'Resposta do backend Python recebida'
    );

    const target = message.from;
    const action = await dispatchResponse(client, target, response || {});
    log.info({ action }, 'Resposta despachada para o WhatsApp');

    return response;
  } catch (err) {
    log.error({ err: err.message }, 'Falha no pipeline da mensagem');
    try {
      await client.sendMessage(message.from, FALLBACK_TEXT);
    } catch (sendErr) {
      log.error({ err: sendErr.message }, 'Falha ao enviar fallback para o aluno');
    }
    return null;
  }
}

module.exports = { handleInboundMessage };
