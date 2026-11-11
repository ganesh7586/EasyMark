/**
 * Webhook Routes for Slack and Teams Bots
 */

const express = require('express');
const router = express.Router();
const webhookController = require('../controllers/webhookController');

// Support urlencoded bodies for Slack slash commands
router.use(express.urlencoded({ extended: true }));

// POST /api/webhooks/slack - Slack Slash Commands & Mentions
router.post('/slack', webhookController.handleSlackWebhook);

// POST /api/webhooks/teams - Microsoft Teams Bot Messages
router.post('/teams', webhookController.handleTeamsWebhook);

module.exports = router;
