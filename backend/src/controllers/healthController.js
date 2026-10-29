/**
 * Health Controller
 * Orchestrates Gateway health checks and probes the downstream Python AI service
 * using the secure x-internal-key authentication bridge.
 */

const axios = require('axios');
const config = require('../config/environment');

const startTime = Date.now();

/**
 * GET /api/health
 * Aggregated health probe for Gateway + Python AI Engine
 */
async function getSystemHealth(req, res) {
  const gatewayUptimeSeconds = Math.floor((Date.now() - startTime) / 1000);
  const memUsage = process.memoryUsage();

  const gatewayInfo = {
    status: 'UP',
    service: 'application-gateway',
    uptimeSeconds: gatewayUptimeSeconds,
    nodeVersion: process.version,
    memory: {
      heapUsedMB: Math.round((memUsage.heapUsed / 1024 / 1024) * 100) / 100,
      heapTotalMB: Math.round((memUsage.heapTotal / 1024 / 1024) * 100) / 100,
      rssMB: Math.round((memUsage.rss / 1024 / 1024) * 100) / 100,
    },
  };

  const probeStart = Date.now();
  let aiServiceInfo = null;
  let bridgeAuthenticated = false;
  let isAiHealthy = false;

  try {
    const response = await axios.get(`${config.aiServiceUrl}/api/v1/health`, {
      headers: {
        'x-internal-key': config.internalApiKey,
      },
      timeout: 3000, // 3-second timeout budget for health probes
    });

    const latencyMs = Date.now() - probeStart;
    bridgeAuthenticated = true;
    isAiHealthy = response.status === 200 && response.data?.status === 'healthy';

    aiServiceInfo = {
      status: isAiHealthy ? 'UP' : 'DEGRADED',
      endpoint: `${config.aiServiceUrl}/api/v1/health`,
      latencyMs,
      data: response.data,
    };
  } catch (error) {
    const latencyMs = Date.now() - probeStart;
    aiServiceInfo = {
      status: 'UNREACHABLE',
      endpoint: `${config.aiServiceUrl}/api/v1/health`,
      latencyMs,
      error: error.response?.data || error.message,
      httpStatus: error.response?.status || null,
    };
  }

  const isOverallHealthy = gatewayInfo.status === 'UP' && isAiHealthy;
  const statusCode = isOverallHealthy ? 200 : 503;

  return res.status(statusCode).json({
    status: isOverallHealthy ? 'healthy' : 'degraded',
    timestamp: new Date().toISOString(),
    bridgeAuthenticated,
    services: {
      gateway: gatewayInfo,
      aiService: aiServiceInfo,
    },
  });
}

/**
 * GET /api/health/live
 * Fast, unauthenticated liveness probe for the Gateway alone
 */
function getGatewayLiveness(req, res) {
  return res.status(200).json({
    status: 'UP',
    service: 'application-gateway',
    timestamp: new Date().toISOString(),
  });
}

module.exports = {
  getSystemHealth,
  getGatewayLiveness,
};
