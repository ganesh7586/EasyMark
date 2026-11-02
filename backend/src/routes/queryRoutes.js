/**
 * Policy Query Routes
 */

const express = require('express');
const router = express.Router();
const queryController = require('../controllers/queryController');

// POST /api/query - Query Static Company Policies with Grounded Citations
router.post('/', queryController.handlePolicyQuery);

module.exports = router;
