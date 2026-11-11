/**
 * Document Controller
 * Proxies document uploads and catalog queries to the Python AI service.
 */

const axios = require('axios');
const config = require('../config/environment');

/**
 * GET /api/documents
 * List all documents currently indexed in vector search.
 */
async function handleListDocuments(req, res, next) {
  try {
    const response = await axios.get(`${config.aiServiceUrl}/api/v1/rag/documents`, {
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
        error: error.response.data?.detail || 'Downstream AI service error',
      });
    }
    next(error);
  }
}

/**
 * POST /api/documents/upload
 * Dynamically ingests a new PDF, TXT, or Markdown document.
 */
async function handleUploadDocument(req, res, next) {
  try {
    const { filename, content_base64, text_content } = req.body;

    if (!filename || typeof filename !== 'string' || !filename.trim()) {
      return res.status(400).json({
        success: false,
        error: "Field 'filename' is required.",
      });
    }

    if (!content_base64 && !text_content) {
      return res.status(400).json({
        success: false,
        error: "Either 'content_base64' or 'text_content' must be supplied.",
      });
    }

    const payload = {
      filename: filename.trim(),
      content_base64: content_base64 || null,
      text_content: text_content || null,
    };

    const response = await axios.post(`${config.aiServiceUrl}/api/v1/rag/upload`, payload, {
      headers: {
        'x-internal-key': config.internalApiKey,
        'Content-Type': 'application/json',
      },
      timeout: 60000, // 60s budget for chunking and dense embeddings
    });

    return res.status(200).json({
      success: true,
      data: response.data,
    });
  } catch (error) {
    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        error: error.response.data?.detail || 'Failed to ingest document',
      });
    }
    next(error);
  }
}

/**
 * DELETE /api/documents/:doc_name
 * Removes a document from the vector index.
 */
async function handleDeleteDocument(req, res, next) {
  try {
    const { doc_name } = req.params;
    const response = await axios.delete(
      `${config.aiServiceUrl}/api/v1/rag/documents/${encodeURIComponent(doc_name)}`,
      {
        headers: { 'x-internal-key': config.internalApiKey },
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
        error: error.response.data?.detail || 'Failed to delete document',
      });
    }
    next(error);
  }
}

module.exports = {
  handleListDocuments,
  handleUploadDocument,
  handleDeleteDocument,
};
