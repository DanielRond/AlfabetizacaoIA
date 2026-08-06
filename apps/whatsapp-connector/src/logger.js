'use strict';

const pino = require('pino');
const config = require('./config');

const logger = pino({
  level: String(config.logLevel).toLowerCase(),
  base: { service: 'whatsapp-connector' },
  timestamp: pino.stdTimeFunctions.isoTime,
});

function childLogger(bindings) {
  return logger.child(bindings || {});
}

module.exports = { logger, childLogger };
