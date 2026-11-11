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

/**
 * POST /api/query/agent
 * Executes the full LangGraph orchestrator workflow across RAG, Live MCP Tools, and Hybrid.
 */
async function handleAgentQuery(req, res, next) {
  try {
    const { query, thread_id = null, user_id = 'employee_default' } = req.body;

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
      thread_id: thread_id ? String(thread_id).trim() : null,
      user_id: user_id ? String(user_id).trim() : 'employee_default',
    };

    const response = await axios.post(`${config.aiServiceUrl}/api/v1/agent/query`, payload, {
      headers: {
        'x-internal-key': config.internalApiKey,
        'Content-Type': 'application/json',
      },
      timeout: 60000,
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
          code: 'AI_AGENT_ERROR',
          message: error.response.data?.detail || 'Downstream LangGraph agent error',
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

/**
 * POST /api/query/evaluate
 * Fast diagnostic query evaluation: returns intent, routing decision, confidence, and tools.
 */
async function handleAgentEvaluate(req, res, next) {
  try {
    const { query } = req.body;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: "Field 'query' must be a non-empty string.",
        },
      });
    }

    const response = await axios.post(
      `${config.aiServiceUrl}/api/v1/agent/evaluate`,
      { query: query.trim() },
      {
        headers: {
          'x-internal-key': config.internalApiKey,
          'Content-Type': 'application/json',
        },
        timeout: 5000,
      }
    );

    return res.status(200).json({
      success: true,
      data: response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        error: {
          code: 'AI_AGENT_ERROR',
          message: error.response.data?.detail || 'Downstream LangGraph evaluation error',
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

/**
 * GET /api/query/threads/:thread_id
 * Retrieves multi-turn conversation checkpoints for a session thread.
 */
async function handleGetThreadHistory(req, res, next) {
  try {
    const { thread_id } = req.params;
    const limit = req.query.limit ? parseInt(req.query.limit, 10) : 20;

    const response = await axios.get(
      `${config.aiServiceUrl}/api/v1/agent/threads/${encodeURIComponent(thread_id)}/history?limit=${limit}`,
      {
        headers: {
          'x-internal-key': config.internalApiKey,
        },
        timeout: 10000,
      }
    );

    return res.status(200).json({
      success: true,
      data: response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        error: {
          code: 'THREAD_HISTORY_ERROR',
          message: error.response.data?.detail || 'Downstream error fetching thread history',
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

/**
 * DELETE /api/query/threads/:thread_id
 * Deletes all checkpoints and clears conversation memory for a thread.
 */
async function handleDeleteThread(req, res, next) {
  try {
    const { thread_id } = req.params;

    const response = await axios.delete(
      `${config.aiServiceUrl}/api/v1/agent/threads/${encodeURIComponent(thread_id)}`,
      {
        headers: {
          'x-internal-key': config.internalApiKey,
        },
        timeout: 10000,
      }
    );

    return res.status(200).json({
      success: true,
      data: response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        error: {
          code: 'THREAD_DELETE_ERROR',
          message: error.response.data?.detail || 'Downstream error deleting thread',
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

/**
 * POST /api/query/agent/stream
 * Streams tokens and execution events from downstream FastAPI directly to the client via SSE.
 */
async function handleAgentStreamQuery(req, res, next) {
  try {
    const { query, thread_id = null, user_id = 'employee_default' } = req.body;

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
      thread_id: thread_id ? String(thread_id).trim() : null,
      user_id: user_id ? String(user_id).trim() : 'employee_default',
    };

    const downstream = await axios.post(`${config.aiServiceUrl}/api/v1/agent/stream`, payload, {
      headers: {
        'x-internal-key': config.internalApiKey,
        'Content-Type': 'application/json',
      },
      responseType: 'stream',
      timeout: 60000,
    });

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');

    downstream.data.pipe(res);

    downstream.data.on('error', (err) => {
      console.error('[Stream Error]', err);
      if (!res.headersSent) {
        res.status(502).json({ success: false, error: 'Stream interrupted' });
      } else {
        res.end();
      }
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        error: {
          code: 'AI_AGENT_ERROR',
          message: 'Downstream LangGraph agent stream error',
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

/**
 * GET /api/query/analytics
 * Retrieve aggregated agent metrics and vector statistics from downstream AI engine.
 */
async function handleGetAnalytics(req, res, next) {
  try {
    const response = await axios.get(`${config.aiServiceUrl}/api/v1/agent/analytics`, {
      headers: { 'x-internal-key': config.internalApiKey },
      timeout: 10000,
    });
    return res.status(200).json({
      success: true,
      data: response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        error: error.response.data?.detail || 'Downstream analytics error',
      });
    }
    next(error);
  }
}

module.exports = {
  handlePolicyQuery,
  handleAgentQuery,
  handleAgentStreamQuery,
  handleAgentEvaluate,
  handleGetThreadHistory,
  handleDeleteThread,
  handleGetAnalytics,
};
