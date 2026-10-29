/**
 * Application Gateway Server
 * Entry point for Node.js Express Gateway (Port 5000)
 */

const express = require('express');
const cors = require('cors');
const config = require('./config/environment');
const healthRoutes = require('./routes/healthRoutes');
const { notFoundHandler, globalErrorHandler } = require('./middleware/errorHandler');

const app = express();

// Security & Parsing Middleware
app.use(
  cors({
    origin: config.clientOrigin,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'x-internal-key'],
  })
);

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Simple request logger
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(
      `[${new Date().toISOString()}] ${req.method} ${req.originalUrl} ${res.statusCode} - ${duration}ms`
    );
  });
  next();
});

// Root welcome route
app.get('/', (req, res) => {
  res.json({
    name: 'Company Intelligence AI Gateway',
    version: '1.0.0',
    status: 'running',
    docs: '/api/health',
  });
});

// Mount Routes
app.use('/api/health', healthRoutes);

// Fallthrough 404 & Global Error Handling
app.use(notFoundHandler);
app.use(globalErrorHandler);

// Start HTTP Server
const server = app.listen(config.port, () => {
  console.log(`========================================================`);
  console.log(`🚀 Gateway Server running on http://localhost:${config.port}`);
  console.log(`   Environment: ${config.nodeEnv}`);
  console.log(`   AI Service Bridge Target: ${config.aiServiceUrl}`);
  console.log(`========================================================`);
});

// Graceful Shutdown Handlers
function handleGracefulShutdown(signal) {
  console.log(`\nReceived ${signal}. Shutting down HTTP server gracefully...`);
  server.close(() => {
    console.log('HTTP server closed. Exiting process.');
    process.exit(0);
  });

  // Force exit if close takes too long
  setTimeout(() => {
    console.error('Forcefully exiting after timeout.');
    process.exit(1);
  }, 5000);
}

process.on('SIGINT', () => handleGracefulShutdown('SIGINT'));
process.on('SIGTERM', () => handleGracefulShutdown('SIGTERM'));

module.exports = { app, server };
