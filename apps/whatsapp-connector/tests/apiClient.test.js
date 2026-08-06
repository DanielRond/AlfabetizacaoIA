'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { postInbound, checkHealth } = require('../src/apiClient');

function fakeResponse(status, body, ok) {
  return {
    ok: ok !== undefined ? ok : status >= 200 && status < 300,
    status,
    async json() {
      return body;
    },
    async text() {
      return JSON.stringify(body);
    },
  };
}

function fakeFetch(handler) {
  const calls = [];
  const impl = async (...args) => {
    calls.push(args);
    return handler(calls.length - 1, args);
  };
  impl.calls = calls;
  return impl;
}

test('postInbound envia payload no endpoint e retorna o JSON', async () => {
  const payload = { message_id: 'x', phone_number: '5511' };
  const fetchImpl = fakeFetch(() => fakeResponse(200, { action: 'noop' }));

  const out = await postInbound(payload, {
    fetchImpl,
    retries: 0,
    retryBaseDelayMs: 1,
    timeoutMs: 5000,
  });

  assert.deepEqual(out, { action: 'noop' });
  assert.equal(fetchImpl.calls.length, 1);
  const [url, options] = fetchImpl.calls[0];
  assert.match(url, /\/v1\/messages\/inbound$/);
  assert.equal(options.method, 'POST');
  assert.equal(JSON.parse(options.body).message_id, 'x');
});

test('postInbound tenta novamente em HTTP 500 e converge', async () => {
  const fetchImpl = fakeFetch((i) =>
    i === 0 ? fakeResponse(500, {}) : fakeResponse(200, { action: 'send_text' })
  );

  const out = await postInbound({}, {
    fetchImpl,
    retries: 2,
    retryBaseDelayMs: 1,
    timeoutMs: 5000,
  });

  assert.deepEqual(out, { action: 'send_text' });
  assert.equal(fetchImpl.calls.length, 2);
});

test('postInbound falha após esgotar retries em HTTP 500', async () => {
  const fetchImpl = fakeFetch(() => fakeResponse(500, {}));

  await assert.rejects(
    () =>
      postInbound({}, {
        fetchImpl,
        retries: 2,
        retryBaseDelayMs: 1,
        timeoutMs: 5000,
      }),
    /HTTP 500/
  );
  assert.equal(fetchImpl.calls.length, 3);
});

test('postInbound não faz retry em erro 4xx', async () => {
  const fetchImpl = fakeFetch(() => fakeResponse(400, { status: 'error' }));

  await assert.rejects(
    () =>
      postInbound({}, {
        fetchImpl,
        retries: 2,
        retryBaseDelayMs: 1,
        timeoutMs: 5000,
      }),
    /HTTP 400/
  );
  assert.equal(fetchImpl.calls.length, 1);
});

test('postInbound tenta novamente em erro de rede e falha no fim', async () => {
  const fetchImpl = fakeFetch(() => {
    throw new Error('ECONNREFUSED');
  });

  await assert.rejects(
    () =>
      postInbound({}, {
        fetchImpl,
        retries: 1,
        retryBaseDelayMs: 1,
        timeoutMs: 5000,
      }),
    /ECONNREFUSED/
  );
  assert.equal(fetchImpl.calls.length, 2);
});

test('checkHealth retorna null quando o backend está fora', async () => {
  const fetchImpl = fakeFetch(() => {
    throw new Error('ECONNREFUSED');
  });
  const out = await checkHealth({ fetchImpl, timeoutMs: 100 });
  assert.equal(out, null);
});

test('checkHealth retorna o JSON de status quando ok', async () => {
  const fetchImpl = fakeFetch(() => fakeResponse(200, { status: 'healthy' }));
  const out = await checkHealth({ fetchImpl, timeoutMs: 100 });
  assert.deepEqual(out, { status: 'healthy' });
});
