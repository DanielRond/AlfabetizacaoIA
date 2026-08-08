'use strict';

const { randomUUID } = require('crypto');
const { normalizeMessage } = require('./normalizer');
const { saveInboundMedia } = require('./media');
const apiClient = require('./apiClient');
const sender = require('./sender');
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

  let response = null;
  try {
    if (normalized.needsMedia) {
      normalized.media_ref = await saveInboundMedia(message, config.mediaDir);
      log.info({ media_ref: normalized.media_ref }, 'Mídia salva para processamento');
    }

    response = await apiClient.postInbound(normalized);
    log.info(
      { action: response && response.action, status: response && response.status },
      'Resposta do backend Python recebida'
    );

    const target = message.from;
    const action = await sender.dispatchResponse(client, target, response || {});
    log.info({ action }, 'Resposta despachada para o WhatsApp');

    await confirmDelivery(normalized, response, action, 'delivered', log);
    return response;
  } catch (err) {
    log.error({ err: err.message }, 'Falha no pipeline da mensagem');
    try {
      await client.sendMessage(message.from, FALLBACK_TEXT);
    } catch (sendErr) {
      log.error({ err: sendErr.message }, 'Falha ao enviar fallback para o aluno');
    }
    await confirmDelivery(normalized, response, null, 'failed', log, err.message);
    return null;
  }
}

// Envia o acknowledgement de entrega ao backend. Nunca lança: é fire-and-forget.
async function confirmDelivery(normalized, response, action, status, log, errorMsg) {
  try {
    const payload = {
      correlation_id: normalized.correlation_id,
      message_id: normalized.message_id,
      phone_number: normalized.phone_number,
      action: action || (response && response.action) || 'noop',
      status,
      media_ref: response && response.media_ref ? response.media_ref : null,
      delivered_at: new Date().toISOString(),
    };
    if (errorMsg) {
      payload.error = errorMsg;
    }
    await apiClient.postDelivered(payload);
  } catch (err) {
    log.warn({ err: err.message }, 'Falha ao confirmar entrega ao backend');
  }
}

module.exports = { handleInboundMessage };
