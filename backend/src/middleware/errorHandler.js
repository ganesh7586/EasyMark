/**
 * Centralized Error Handling Middleware
 */

const config = require('../config/environment');

function notFoundHandler(req, res, next) {
  res.status(404).json({
    success: false,
    error: {
      code: 'ROUTE_NOT_FOUND',
      message: `Cannot ${req.method} ${req.originalUrl}`,
    },
  });
}

function globalErrorHandler(err, req, res, next) {
  const statusCode = err.statusCode || err.status || 500;
  const message = err.message || 'Internal Server Error';

  console.error(`[ERROR] [${new Date().toISOString()}] ${req.method} ${req.originalUrl}:`, err);

  res.status(statusCode).json({
    success: false,
    error: {
      code: err.code || 'INTERNAL_SERVER_ERROR',
      message: message,
      ...(config.isProduction ? {} : { stack: err.stack }),
    },
  });
}

module.exports = {
  notFoundHandler,
  globalErrorHandler,
};
