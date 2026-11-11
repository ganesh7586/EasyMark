/**
 * Document Routes
 */

const express = require('express');
const router = express.Router();
const documentController = require('../controllers/documentController');

// GET /api/documents - List all indexed documents
router.get('/', documentController.handleListDocuments);

// POST /api/documents/upload - Dynamic document ingestion
router.post('/upload', documentController.handleUploadDocument);

// DELETE /api/documents/:doc_name - Purge document
router.delete('/:doc_name', documentController.handleDeleteDocument);

module.exports = router;
