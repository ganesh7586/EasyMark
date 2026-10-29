/**
 * Application Environment Configuration
 * Validates and exposes validated environment variables for the Express Gateway.
 */

const path = require('path');
const dotenv = require('dotenv');

// Load .env file from backend root
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const requiredVariables = ['INTERNAL_API_KEY'];

// Fail-fast verification for critical security configuration
for (const varName of requiredVariables) {
  if (!process.env[varName]) {
    throw new Error(
      `[FATAL CONFIG ERROR] Missing required environment variable: ${varName}. ` +
      `Check your backend/.env configuration file.`
    );
  }
}

const config = Object.freeze({
  port: parseInt(process.env.PORT, 10) || 5000,
  nodeEnv: process.env.NODE_ENV || 'development',
  isProduction: process.env.NODE_ENV === 'production',
  clientOrigin: process.env.CLIENT_ORIGIN || 'http://localhost:5173',
  aiServiceUrl: (process.env.AI_SERVICE_URL || 'http://localhost:8000').replace(/\/+$/, ''),
  internalApiKey: process.env.INTERNAL_API_KEY,
});

module.exports = config;
