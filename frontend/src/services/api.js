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

/**
 * Stream LangGraph Agent response in real-time via Server-Sent Events (SSE).
 */
export async function streamAgentQuery(
  query,
  threadId = null,
  userId = 'employee_default',
  { onMetadata, onChunk, onCitations, onTrace, onDone, onError } = {}
) {
  try {
    const response = await fetch('/api/query/agent/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        thread_id: threadId,
        user_id: userId,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err?.error?.message || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop(); // Retain remainder in buffer

      for (const eventStr of events) {
        if (!eventStr.trim()) continue;
        const lines = eventStr.split('\n');
        let eventType = 'message';
        let dataStr = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            dataStr = line.slice(6).trim();
          }
        }

        if (dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            if (eventType === 'metadata' && onMetadata) onMetadata(parsed);
            if (eventType === 'chunk' && onChunk) onChunk(parsed.token);
            if (eventType === 'citations' && onCitations) onCitations(parsed);
            if (eventType === 'trace' && onTrace) onTrace(parsed.execution_trace);
            if (eventType === 'done' && onDone) onDone(parsed);
          } catch (e) {
            console.warn('Could not parse SSE event payload', e);
          }
        }
      }
    }
  } catch (error) {
    if (onError) onError(error);
    else throw error;
  }
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

export async function getDocuments() {
  const response = await api.get('/documents');
  return response.data;
}

export async function uploadDocument(filename, contentBase64 = null, textContent = null) {
  const response = await api.post('/documents/upload', {
    filename,
    content_base64: contentBase64,
    text_content: textContent,
  });
  return response.data;
}

export async function deleteDocument(docName) {
  const response = await api.delete(`/documents/${encodeURIComponent(docName)}`);
  return response.data;
}

export async function getAnalytics() {
  const response = await api.get('/query/analytics');
  return response.data;
}

export default api;
