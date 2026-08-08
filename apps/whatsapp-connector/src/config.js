'use strict';

const path = require('path');
const dotenv = require('dotenv');

const workspaceRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(workspaceRoot, '..', '..');

// Carrega o .env local do workspace do conector (se existir), com prioridade.
dotenv.config({ path: path.resolve(workspaceRoot, '.env') });
// Fallback: .env da raiz do repositório (configuração compartilhada em dev).
dotenv.config({ path: path.resolve(repoRoot, '.env') });

const config = {
  workspaceRoot,
  repoRoot,
  pythonApiUrl: process.env.PYTHON_API_URL || 'http://localhost:5000',
  sessionDir: path.resolve(workspaceRoot, process.env.WHATSAPP_SESSION_DIR || '.wwebjs_auth'),
  mediaDir: path.resolve(repoRoot, process.env.WHATSAPP_MEDIA_DIR || 'data/media_in'),
  mediaBaseDir: process.env.MEDIA_BASE_DIR ? path.resolve(process.env.MEDIA_BASE_DIR) : repoRoot,
  mediaRetentionMs: Number(process.env.MEDIA_RETENTION_HOURS || 24) * 3600 * 1000,
  browserPath: process.env.WHATSAPP_BROWSER_PATH || null,
  logLevel: process.env.LOG_LEVEL || 'info',
  requestTimeoutMs: Number(process.env.REQUEST_TIMEOUT_MS || 120000),
  retries: Number(process.env.REQUEST_RETRIES || 2),
  retryBaseDelayMs: Number(process.env.RETRY_BASE_DELAY_MS || 500),
};

module.exports = config;
