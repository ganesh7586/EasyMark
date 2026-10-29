/**
 * Health Check Routes
 */

const express = require('express');
const router = express.Router();
const healthController = require('../controllers/healthController');

// Full aggregated system health check (Gateway + AI Service via x-internal-key bridge)
router.get('/', healthController.getSystemHealth);

// Lightweight Gateway-only liveness check
router.get('/live', healthController.getGatewayLiveness);

module.exports = router;
