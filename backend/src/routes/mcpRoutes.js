/**
 * MCP Router for Express Gateway
 */

const express = require('express');
const { listTools, getSchema, getCategories, callTool } = require('../controllers/mcpController');

const router = express.Router();

router.get('/tools', listTools);
router.get('/schema', getSchema);
router.get('/categories', getCategories);
router.post('/tools/call', callTool);

module.exports = router;
