/**
 * MCP Gateway Controller
 * Proxies Model Context Protocol requests to the FastAPI AI Service downstream.
 */

const axios = require('axios');
const config = require('../config/environment');

/**
 * List all available MCP tools and their schemas.
 */
async function listTools(req, res, next) {
  try {
    const response = await axios.get(`${config.aiServiceUrl}/api/v1/mcp/tools`, {
      headers: {
        'x-internal-key': config.internalApiKey,
      },
      timeout: 5000,
    });

    return res.status(200).json({
      status: 'success',
      ...response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    }
    return next(error);
  }
}

/**
 * Execute a specific MCP tool with parameters.
 */
async function callTool(req, res, next) {
  try {
    const { name, arguments: toolArgs } = req.body;
    if (!name) {
      return res.status(400).json({
        error: 'Bad Request',
        message: "Missing required field 'name' for MCP tool execution.",
      });
    }

    const response = await axios.post(
      `${config.aiServiceUrl}/api/v1/mcp/tools/call`,
      {
        name,
        arguments: toolArgs || {},
      },
      {
        headers: {
          'x-internal-key': config.internalApiKey,
          'Content-Type': 'application/json',
        },
        timeout: 10000,
      }
    );

    return res.status(200).json({
      status: 'success',
      result: response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    }
    return next(error);
  }
}

module.exports = {
  listTools,
  callTool,
};
