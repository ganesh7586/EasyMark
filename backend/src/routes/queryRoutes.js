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

// POST /api/query/evaluate - Fast Diagnostic Question Intent & Routing Evaluation
router.post('/evaluate', queryController.handleAgentEvaluate);

module.exports = router;
