/**
 * Gateway API Service
 * Connects React Frontend with the Node.js Express Application Gateway (Port 5000)
 */

import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function queryAgent(query, threadId = null, userId = 'employee_default') {
  const payload = { query, thread_id: threadId, user_id: userId };
  const response = await api.post('/query/agent', payload);
  return response.data;
}

export async function evaluateQuery(query) {
  const response = await api.post('/query/evaluate', { query });
  return response.data;
}

export async function getThreadHistory(threadId) {
  const response = await api.get(`/query/threads/${encodeURIComponent(threadId)}`);
  return response.data;
}

export async function deleteThread(threadId) {
  const response = await api.delete(`/query/threads/${encodeURIComponent(threadId)}`);
  return response.data;
}

export async function getGatewayHealth() {
  const response = await api.get('/health');
  return response.data;
}

export async function getMCPCategories() {
  const response = await api.get('/mcp/categories');
  return response.data;
}

export default api;
