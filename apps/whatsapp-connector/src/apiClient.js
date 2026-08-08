'use strict';

const config = require('./config');

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function postInbound(payload, opts = {}) {
  const url = `${opts.pythonApiUrl || config.pythonApiUrl}/v1/messages/inbound`;
  const timeoutMs = opts.timeoutMs || config.requestTimeoutMs;
  const retries = opts.retries ?? config.retries;
  const retryBaseDelayMs = opts.retryBaseDelayMs ?? config.retryBaseDelayMs;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;

  let lastError;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const res = await fetchImpl(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (res.ok) {
          return await res.json().catch(() => null);
        }

        const status = res.status;
        const body = await res.text().catch(() => '');
        if (status >= 400 && status <= 499) {
          const err = new Error(`Backend Python retornou HTTP ${status}`);
          err.status = status;
          err.body = body;
          err.retryable = false;
          throw err;
        }
        if (attempt >= retries) {
          const err = new Error(`HTTP ${status} no backend Python`);
          err.status = status;
          err.retryable = true;
          throw err;
        }
        lastError = new Error(`HTTP ${status} no backend Python`);
        lastError.status = status;
      } finally {
        clearTimeout(timer);
      }
    } catch (err) {
      if (err && err.retryable === false) {
        throw err;
      }
      lastError = err;
    }

    if (attempt < retries) {
      await sleep(retryBaseDelayMs * 2 ** attempt);
    }
  }

  throw lastError;
}

// Fire-and-forget: confirma entrega ao backend. Nunca lança.
async function postDelivered(payload, opts = {}) {
  const url = `${opts.pythonApiUrl || config.pythonApiUrl}/v1/messages/delivered`;
  const timeoutMs = opts.timeoutMs || 5000;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetchImpl(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      return res.ok ? res.status : null;
    } finally {
      clearTimeout(timer);
    }
  } catch {
    return null;
  }
}

async function checkHealth(opts = {}) {
  const url = `${opts.pythonApiUrl || config.pythonApiUrl}/health`;
  const timeoutMs = opts.timeoutMs || 5000;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetchImpl(url, { signal: controller.signal });
      return res.ok ? await res.json() : null;
    } finally {
      clearTimeout(timer);
    }
  } catch {
    return null;
  }
}

module.exports = { postInbound, postDelivered, checkHealth };
