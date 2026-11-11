/**
 * Complete End-to-End System Integration Test
 * Starts FastAPI AI Service & Express Gateway, executes 24 multi-tier probes, and exits cleanly.
 */

const { spawn } = require('child_process');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const FASTAPI_DIR = path.join(ROOT_DIR, 'ai-service');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');
const PYTHON_EXE = path.join(FASTAPI_DIR, 'venv', 'Scripts', 'python.exe');

const FASTAPI_URL = 'http://127.0.0.1:8000';
const GATEWAY_URL = 'http://127.0.0.1:5000';
const INTERNAL_KEY = 'company_intel_internal_sec_token_2026_9f8e7d';
const TEST_THREAD_ID = `e2e_thread_${Date.now()}`;

let fastApiProcess = null;
let expressProcess = null;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer(url, timeoutMs = 90000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.status === 200) {
        return true;
      }
    } catch (err) {
      // Server not ready yet
    }
    await sleep(500);
  }
  throw new Error(`Timeout waiting for server at ${url}`);
}

async function runTestSuite() {
  console.log('='.repeat(78));
  console.log('   COMPANY INTELLIGENCE AI - COMPLETE SYSTEM END-TO-END VERIFICATION');
  console.log('='.repeat(78));

  // 1. Launch FastAPI AI Service
  console.log('\n[1/4] Spawning FastAPI AI Service downstream (Port 8000)...');
  fastApiProcess = spawn(
    PYTHON_EXE,
    ['-u', '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
    {
      cwd: FASTAPI_DIR,
      env: { ...process.env, PYTHONPATH: FASTAPI_DIR, PYTHONUNBUFFERED: '1', MONGODB_URI: 'mock' },
      stdio: 'inherit',
    }
  );

  fastApiProcess.on('exit', (code) => {
    console.log('  [FastAPI exited with code]', code);
  });

  await waitForServer(`${FASTAPI_URL}/health`);
  console.log('  -> FastAPI AI Service is online and healthy.');

  // 2. Launch Express Gateway
  console.log('\n[2/4] Spawning Node.js Express Gateway upstream (Port 5000)...');
  expressProcess = spawn('node', ['src/server.js'], {
    cwd: BACKEND_DIR,
    env: { ...process.env, PORT: '5000', AI_SERVICE_URL: FASTAPI_URL, INTERNAL_API_KEY: INTERNAL_KEY },
    stdio: 'inherit',
  });

  await waitForServer(`${GATEWAY_URL}/health`);
  console.log('  -> Express Gateway is online and healthy.');

  // 3. Execute Probes
  console.log('\n[3/4] Executing Multi-Tier Integration Probes across Gateway & AI Service...\n');

  const tests = [
    {
      name: 'Direct FastAPI Public Liveness Probe (/health)',
      url: `${FASTAPI_URL}/health`,
      method: 'GET',
      headers: {},
      validate: (data, status) => status === 200 && data.status === 'healthy',
    },
    {
      name: 'Direct FastAPI Readiness Probe without Key (/api/v1/health -> 401)',
      url: `${FASTAPI_URL}/api/v1/health`,
      method: 'GET',
      headers: {},
      validate: (data, status) => status === 401,
    },
    {
      name: 'Direct FastAPI Readiness Probe with Key (/api/v1/health -> 200)',
      url: `${FASTAPI_URL}/api/v1/health`,
      method: 'GET',
      headers: { 'x-internal-key': INTERNAL_KEY },
      validate: (data, status) => status === 200 && data.status === 'healthy',
    },
    {
      name: 'Express Gateway Public Liveness (/health)',
      url: `${GATEWAY_URL}/health`,
      method: 'GET',
      headers: {},
      validate: (data, status) => status === 200 && data.status === 'healthy',
    },
    {
      name: 'Express Bridge to FastAPI Readiness Probe (/api/health)',
      url: `${GATEWAY_URL}/api/health`,
      method: 'GET',
      headers: {},
      validate: (data, status) => status === 200 && data.bridgeAuthenticated === true,
    },
    {
      name: 'Express Bridge to List MCP Tools (/api/mcp/tools -> 15 Tools)',
      url: `${GATEWAY_URL}/api/mcp/tools`,
      method: 'GET',
      headers: {},
      validate: (data, status) => status === 200 && data.count === 15 && data.tools.length === 15,
    },
    {
      name: 'Express Bridge to OpenAI/Groq Tool Schema (/api/mcp/schema)',
      url: `${GATEWAY_URL}/api/mcp/schema`,
      method: 'GET',
      headers: {},
      validate: (data, status) => status === 200 && data.count === 15 && data.tools[0].type === 'function',
    },
    {
      name: 'Express Bridge to MCP Categories Breakdown (/api/mcp/categories)',
      url: `${GATEWAY_URL}/api/mcp/categories`,
      method: 'GET',
      headers: {},
      validate: (data, status) =>
        status === 200 &&
        data.categories.jira.length === 4 &&
        data.categories.notion.length === 4 &&
        data.categories.gmail.length === 4 &&
        data.categories.diagnostic.length === 3,
    },
    {
      name: 'Express Tool Execution: jira_get_blockers (Detects ALPHA-101)',
      url: `${GATEWAY_URL}/api/mcp/tools/call`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'jira_get_blockers', arguments: {} }),
      validate: (data, status) =>
        status === 200 &&
        data.result.isError === false &&
        data.result.content[0].text.includes('ALPHA-101'),
    },
    {
      name: 'Express Tool Execution: notion_get_page (Fetches NOTION-SPEC-01)',
      url: `${GATEWAY_URL}/api/mcp/tools/call`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'notion_get_page',
        arguments: { page_id_or_title: 'NOTION-SPEC-01' },
      }),
      validate: (data, status) =>
        status === 200 &&
        data.result.isError === false &&
        data.result.content[0].text.includes('Project Alpha'),
    },
    {
      name: 'Express Tool Execution: gmail_get_customer_escalations (Acme Corp 504)',
      url: `${GATEWAY_URL}/api/mcp/tools/call`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'gmail_get_customer_escalations',
        arguments: { severity: 'SEV-1' },
      }),
      validate: (data, status) =>
        status === 200 &&
        data.result.isError === false &&
        data.result.content[0].text.includes('Acme Corp'),
    },
    {
      name: 'Express Static RAG Query Bridge (/api/query)',
      url: `${GATEWAY_URL}/api/query`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'What are the core collaboration hours?' }),
      validate: (data, status) =>
        status === 200 &&
        data.success === true &&
        data.data &&
        data.data.citations.length >= 1 &&
        data.data.answer.length > 20,
    },
    {
      name: 'Express LangGraph Router Evaluation Bridge (/api/query/evaluate)',
      url: `${GATEWAY_URL}/api/query/evaluate`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'What is the vacation policy notice window?' }),
      validate: (data, status) => {
        const payload = data.data || data;
        return (
          status === 200 &&
          data.success === true &&
          (payload.route === 'static_rag' || payload.routing === 'static_rag')
        );
      },
    },
    {
      name: 'Express LangGraph Agent: Blocker Discovery (Turn 1)',
      url: `${GATEWAY_URL}/api/query/agent`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: 'What blocker issue is currently open in Jira?',
        thread_id: TEST_THREAD_ID,
        user_id: 'employee_test',
      }),
      validate: (data, status) => {
        const payload = data.data || data;
        const answerText = payload.answer || payload.response || '';
        return (
          status === 200 &&
          data.success === true &&
          answerText &&
          (answerText.includes('ALPHA-101') || answerText.includes('ALPHA-104') || answerText.includes('ALPHA')) &&
          payload.thread_id === TEST_THREAD_ID
        );
      },
    },
    {
      name: 'Express LangGraph Agent: Pronoun Coreference Resolution (Turn 2)',
      url: `${GATEWAY_URL}/api/query/agent`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: 'What is its priority and status?',
        thread_id: TEST_THREAD_ID,
        user_id: 'employee_test',
      }),
      validate: (data, status) => {
        const payload = data.data || data;
        return (
          status === 200 &&
          data.success === true &&
          payload.resolved_query &&
          payload.resolved_query.includes('ALPHA')
        );
      },
    },
    {
      name: 'Express Checkpoint History Audit (/api/query/threads/:thread_id)',
      url: `${GATEWAY_URL}/api/query/threads/${TEST_THREAD_ID}`,
      method: 'GET',
      headers: {},
      validate: (data, status) => {
        const payload = data.data || data;
        return (
          status === 200 &&
          data.success === true &&
          payload.thread_id === TEST_THREAD_ID &&
          Array.isArray(payload.history) &&
          payload.history.length >= 2
        );
      },
    },
    {
      name: 'Express LangGraph Real-time SSE Token Streaming (/api/query/agent/stream)',
      url: `${GATEWAY_URL}/api/query/agent/stream`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: 'What is the vacation policy notice window?',
        thread_id: TEST_THREAD_ID,
        user_id: 'employee_test',
      }),
      isStream: true,
      validateText: (text, status) => {
        return (
          status === 200 &&
          text.includes('event: metadata') &&
          text.includes('event: chunk') &&
          text.includes('event: citations') &&
          text.includes('event: done')
        );
      },
    },
    {
      name: 'Express Dynamic Document Catalog Listing (GET /api/documents)',
      url: `${GATEWAY_URL}/api/documents`,
      method: 'GET',
      headers: {},
      validate: (data, status) => {
        return (
          status === 200 &&
          data.success === true &&
          Array.isArray(data.data) &&
          data.data.length >= 1
        );
      },
    },
    {
      name: 'Express Dynamic Ingestion of Markdown Document (POST /api/documents/upload)',
      url: `${GATEWAY_URL}/api/documents/upload`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: 'e2e_security_sop.md',
        text_content: '# Enterprise Security SOP\nAll production cluster deployments require mandatory hardware key MFA and dual-engineer signoff.',
      }),
      validate: (data, status) => {
        return (
          status === 200 &&
          data.success === true &&
          data.data.filename === 'e2e_security_sop.md' &&
          data.data.total_chunks >= 1 &&
          data.data.status === 'indexed'
        );
      },
    },
    {
      name: 'Express Dynamic Document Purge / Teardown (DELETE /api/documents/:doc_name)',
      url: `${GATEWAY_URL}/api/documents/e2e_security_sop.md`,
      method: 'DELETE',
      headers: {},
      validate: (data, status) => {
        return (
          status === 200 &&
          data.success === true &&
          data.data.doc_name === 'e2e_security_sop.md' &&
          data.data.status === 'purged'
        );
      },
    },
    {
      name: 'Express Enterprise Analytics & Routing Observability (GET /api/query/analytics)',
      url: `${GATEWAY_URL}/api/query/analytics`,
      method: 'GET',
      headers: {},
      validate: (data, status) => {
        return (
          status === 200 &&
          data.success === true &&
          data.data.status === 'operational' &&
          data.data.vector_store != null &&
          data.data.benchmarks != null &&
          Array.isArray(data.data.supported_routes)
        );
      },
    },
    {
      name: 'Express Slack Webhook Slash Command (/easymark) with Block Kit',
      url: `${GATEWAY_URL}/api/webhooks/slack`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: 'What are the core work hours?',
        user_name: 'slack_alice',
        channel_id: 'general_ops',
      }),
      validate: (data, status) => {
        return (
          status === 200 &&
          data.response_type === 'in_channel' &&
          Array.isArray(data.blocks) &&
          data.blocks.length >= 2
        );
      },
    },
    {
      name: 'Express Microsoft Teams Webhook Adapter with Adaptive Card',
      url: `${GATEWAY_URL}/api/webhooks/teams`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: 'What is the vacation policy?',
        from: { name: 'teams_bob' },
      }),
      validate: (data, status) => {
        return (
          status === 200 &&
          data.type === 'message' &&
          Array.isArray(data.attachments) &&
          data.attachments[0].contentType === 'application/vnd.microsoft.card.adaptive' &&
          data.attachments[0].content.type === 'AdaptiveCard'
        );
      },
    },
    {
      name: 'Express Thread Teardown & Purge (DELETE /api/query/threads/:thread_id)',
      url: `${GATEWAY_URL}/api/query/threads/${TEST_THREAD_ID}`,
      method: 'DELETE',
      headers: {},
      validate: (data, status) => {
        const payload = data.data || data;
        return (
          status === 200 &&
          data.success === true &&
          (payload.status === 'cleared' || payload.deleted === true)
        );
      },
    },
  ];

  let passed = 0;
  let failed = 0;

  for (let i = 0; i < tests.length; i++) {
    const t = tests[i];
    const start = Date.now();
    try {
      const res = await fetch(t.url, {
        method: t.method,
        headers: t.headers,
        body: t.body,
      });
      const duration = Date.now() - start;
      let ok = false;
      let rawData = null;

      if (t.isStream) {
        const text = await res.text();
        rawData = text;
        ok = t.validateText(text, res.status);
      } else {
        const data = await res.json().catch(() => ({}));
        rawData = data;
        ok = t.validate(data, res.status);
      }

      if (ok) {
        console.log(`  [PASS] Probe #${i + 1}: ${t.name} (${duration} ms)`);
        passed++;
      } else {
        console.error(`  [FAIL] Probe #${i + 1}: ${t.name} (${duration} ms) - Status: ${res.status}`);
        console.error('         Received payload:', JSON.stringify(rawData).slice(0, 160));
        failed++;
      }
    } catch (err) {
      console.error(`  [ERROR] Probe #${i + 1}: ${t.name} - ${err.message}`);
      failed++;
    }
  }

  console.log('\n' + '='.repeat(78));
  console.log(`[4/4] COMPLETE SYSTEM TEST RESULTS: ${passed} PASSED | ${failed} FAILED`);
  console.log('='.repeat(78));

  if (failed > 0) {
    process.exitCode = 1;
  }
}

async function shutdown() {
  console.log('\n[Shutdown] Terminating child server processes cleanly...');
  if (expressProcess) {
    expressProcess.kill('SIGTERM');
  }
  if (fastApiProcess) {
    fastApiProcess.kill('SIGTERM');
  }
  await sleep(1000);
}

runTestSuite()
  .catch((err) => {
    console.error('FATAL Test Suite Error:', err);
    process.exitCode = 1;
  })
  .finally(async () => {
    await shutdown();
    process.exit(process.exitCode || 0);
  });
