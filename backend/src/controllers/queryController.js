/**
 * Query Controller
 * Proxies user policy questions to the Python AI service across the secure internal bridge.
 */

const axios = require('axios');
const config = require('../config/environment');

/**
 * POST /api/query
 * Dispatches a natural language question to the Python RAG engine.
 */
async function handlePolicyQuery(req, res, next) {
  try {
    const { query, top_k = 4, doc_filter = null } = req.body;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: "Field 'query' must be a non-empty string.",
        },
      });
    }

    const payload = {
      query: query.trim(),
      top_k: Math.min(Math.max(parseInt(top_k, 10) || 4, 1), 10),
      doc_filter: doc_filter ? String(doc_filter).trim() : null,
    };

    // Forward to Python AI Service with internal security key
    const response = await axios.post(`${config.aiServiceUrl}/api/v1/rag/query`, payload, {
      headers: {
        'x-internal-key': config.internalApiKey,
        'Content-Type': 'application/json',
      },
      timeout: 60000, // 60-second budget for LLM inference & neural embedding
    });

    return res.status(200).json({
      success: true,
      data: response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        error: {
          code: 'AI_SERVICE_ERROR',
          message: error.response.data?.detail || 'Downstream AI engine error',
        },
      });
    }

    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
      return res.status(503).json({
        success: false,
        error: {
          code: 'AI_SERVICE_UNAVAILABLE',
          message: 'The AI compute engine on Port 8000 is unreachable.',
        },
      });
    }

    next(error);
  }
}

module.exports = {
  handlePolicyQuery,
};
