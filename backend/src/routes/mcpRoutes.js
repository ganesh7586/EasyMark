/**
 * MCP Router for Express Gateway
 */

const express = require('express');
const { listTools, callTool } = require('../controllers/mcpController');

const router = express.Router();

router.get('/tools', listTools);
router.post('/tools/call', callTool);

module.exports = router;
