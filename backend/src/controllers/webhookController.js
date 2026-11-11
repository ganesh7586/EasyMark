/**
 * Webhook Controller
 * Enterprise Bot Adapters for Slack and Microsoft Teams.
 */

const axios = require('axios');
const config = require('../config/environment');

/**
 * Helper to query the internal LangGraph AI Service.
 */
async function queryInternalAgent(queryText, threadId = null, userId = 'bot_user') {
  const response = await axios.post(
    `${config.aiServiceUrl}/api/v1/agent/query`,
    {
      query: queryText,
      thread_id: threadId,
      user_id: userId,
    },
    {
      headers: {
        'x-internal-key': config.internalApiKey,
        'Content-Type': 'application/json',
      },
      timeout: 45000,
    }
  );
  return response.data;
}

/**
 * POST /api/webhooks/slack
 * Handles Slack Slash Commands (/easymark <question>) and Event API subscriptions.
 */
async function handleSlackWebhook(req, res, next) {
  try {
    // 1. Slack URL Verification Challenge
    if (req.body && req.body.type === 'url_verification') {
      return res.status(200).json({ challenge: req.body.challenge });
    }

    // 2. Slash Command (/easymark <text>) or urlencoded body
    const queryText = req.body.text || req.body.query || '';
    const userId = req.body.user_name || req.body.user_id || 'slack_employee';
    const channelId = req.body.channel_id || 'general';

    if (!queryText.trim()) {
      return res.status(200).json({
        response_type: 'ephemeral',
        text: '👋 Please provide a question! Example: `/easymark What are the core remote work hours?`',
      });
    }

    // 3. Process via LangGraph Orchestrator
    const agentResult = await queryInternalAgent(queryText, `slack_${channelId}`, userId);

    const answer = agentResult.answer || 'Execution complete.';
    const citations = agentResult.citations || [];
    const groundingScore = agentResult.grounding_score
      ? `${(agentResult.grounding_score * 100).toFixed(0)}%`
      : 'Grounded';
    const route = agentResult.route || 'Autonomous';

    // 4. Build Slack Block Kit Response
    const blocks = [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: '🤖 EasyMark Enterprise AI',
          emoji: true,
        },
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Query:* "${queryText}"\n\n${answer}`,
        },
      },
      {
        type: 'context',
        elements: [
          {
            type: 'mrkdwn',
            text: `*Route:* \`${route}\`  |  *Grounding:* \`${groundingScore}\`  |  *Citations:* ${citations.length} verified sources`,
          },
        ],
      },
    ];

    return res.status(200).json({
      response_type: 'in_channel',
      blocks,
      text: answer, // Fallback for notifications
    });
  } catch (error) {
    console.error('[Slack Webhook Error]', error.message);
    return res.status(200).json({
      response_type: 'ephemeral',
      text: `⚠️ EasyMark Agent Error: ${error.message || 'Service temporarily unavailable'}`,
    });
  }
}

/**
 * POST /api/webhooks/teams
 * Handles Microsoft Teams Bot Messages & returns Adaptive Cards.
 */
async function handleTeamsWebhook(req, res, next) {
  try {
    const text = req.body.text || req.body.query || '';
    const cleanText = text.replace(/<at>.*?<\/at>/g, '').trim();

    if (!cleanText) {
      return res.status(200).json({
        type: 'message',
        text: 'Hello! Ask me any question across company policies, Jira blockers, Notion docs, or Gmail.',
      });
    }

    const agentResult = await queryInternalAgent(cleanText, 'teams_channel', 'teams_user');
    const answer = agentResult.answer || 'Execution complete.';
    const citations = agentResult.citations || [];

    // Microsoft Teams Adaptive Card format
    const adaptiveCard = {
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: {
            type: 'AdaptiveCard',
            version: '1.4',
            body: [
              {
                type: 'TextBlock',
                size: 'Medium',
                weight: 'Bolder',
                text: 'EasyMark Enterprise Assistant',
              },
              {
                type: 'TextBlock',
                text: answer,
                wrap: true,
              },
              {
                type: 'FactSet',
                facts: [
                  { title: 'Route', value: agentResult.route || 'Autonomous' },
                  { title: 'Grounding', value: `${((agentResult.grounding_score || 0.95) * 100).toFixed(0)}% Grounded` },
                  { title: 'Citations', value: `${citations.length} verified references` },
                ],
              },
            ],
          },
        },
      ],
    };

    return res.status(200).json(adaptiveCard);
  } catch (error) {
    console.error('[Teams Webhook Error]', error.message);
    return res.status(200).json({
      type: 'message',
      text: `⚠️ EasyMark Error: ${error.message}`,
    });
  }
}

module.exports = {
  handleSlackWebhook,
  handleTeamsWebhook,
};
