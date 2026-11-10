/**
 * Policy Query Routes
 */

const express = require('express');
const router = express.Router();
const queryController = require('../controllers/queryController');

// POST /api/query - Query Static Company Policies with Grounded Citations
router.post('/', queryController.handlePolicyQuery);

// POST /api/query/agent - Full LangGraph Multi-Agent Orchestrator
router.post('/agent', queryController.handleAgentQuery);

// POST /api/query/agent/stream - Real-time Server-Sent Events (SSE) Streaming
router.post('/agent/stream', queryController.handleAgentStreamQuery);

// POST /api/query/evaluate - Fast Diagnostic Question Intent & Routing Evaluation
router.post('/evaluate', queryController.handleAgentEvaluate);

// GET /api/query/threads/:thread_id - Retrieve Session Checkpoints & History
router.get('/threads/:thread_id', queryController.handleGetThreadHistory);

// DELETE /api/query/threads/:thread_id - Reset / Clear Session Memory
router.delete('/threads/:thread_id', queryController.handleDeleteThread);

module.exports = router;
