# EasyMark Live Cloud API Setup & Integration Guide

EasyMark features a **Dual-Mode Architecture**:
1. **Live Cloud API Mode**: Connects directly to external software services (Jira Cloud, Notion Workspaces, Google Workspace Gmail, and Groq Cloud) to query real-time production issues, meeting notes, customer escalations, and generate streaming answers.
2. **Deterministic Enterprise Fixture Mode**: When external credentials are not set or when operating in an offline environment, EasyMark automatically falls back to the high-fidelity **Project Alpha Enterprise Dataset** (matching company HR, Engineering SLA, and Charter policies) with zero crashes.

---

## 1. Groq Cloud API Key (Free)
> Provides ultra-fast inference ($>500\text{ tokens/sec}$) using `llama-3.3-70b-versatile`.

1. Go to [Groq Cloud Console](https://console.groq.com/).
2. Sign in with GitHub or Google.
3. In the left navigation, click **API Keys**.
4. Click **Create API Key**, name it `EasyMark-Agent`, and copy the token (starts with `gsk_`).
5. Open `ai-service/.env` and update:
   ```env
   GROQ_API_KEY="gsk_your_actual_key_here"
   GROQ_MODEL="llama-3.3-70b-versatile"
   ```

---

## 2. Atlassian Jira Cloud API Token (Free)
> Connects EasyMark to your real Atlassian Jira Cloud workspace to fetch active sprint issues, backlog tickets, and SEV-1 blockers.

### Free Atlassian Account Setup
1. Create a free Jira Cloud workspace at [atlassian.com/software/jira](https://www.atlassian.com/software/jira/free) (free for up to 10 users).
2. Note your workspace URL (e.g. `https://your-company.atlassian.net`).

### Generate API Token
1. Log in to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Click **Create API token**.
3. Label it `EasyMark-MCP-Bridge` and click **Create**.
4. Copy the generated token.

### Configure EasyMark
In `ai-service/.env`:
```env
JIRA_BASE_URL="https://your-company.atlassian.net"
JIRA_EMAIL="your-email@company.com"
JIRA_API_TOKEN="your_atlassian_api_token"
JIRA_PROJECT_KEY="ALPHA"
```

---

## 3. Notion Workspace Integration Token (Free)
> Enables EasyMark to search real Notion pages, specs, product requirement documents (PRDs), and weekly meeting notes.

### Free Notion Workspace Setup
1. Sign in to your Notion account at [notion.so](https://www.notion.so).
2. Create or select a workspace.

### Create Internal Integration Token
1. Navigate to [notion.so/profile/integrations](https://www.notion.so/profile/integrations).
2. Click **+ New integration**.
3. Name it `EasyMark Intelligence Agent`.
4. Select your workspace and grant **Read content** capabilities.
5. Click **Submit** and copy the **Internal Integration Secret** (starts with `secret_`).

### Share Pages with Integration
1. In your Notion workspace, open the pages or databases you want EasyMark to read.
2. In the top-right corner, click **...** (More options) $\rightarrow$ **Connections** $\rightarrow$ **Connect to** $\rightarrow$ select `EasyMark Intelligence Agent`.

### Configure EasyMark
In `ai-service/.env`:
```env
NOTION_API_KEY="secret_your_notion_secret_token"
NOTION_DATABASE_ID="optional_database_id"
```

---

## 4. Google Workspace / Gmail API (Free)
> Allows the agent to query real customer escalation threads, executive emails, and approval notices.

### Google Cloud Console Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com/).
2. Create a project named `EasyMark-Enterprise`.
3. In the sidebar, navigate to **APIs & Services** $\rightarrow$ **Library**.
4. Search for **Gmail API** and click **Enable**.

### Create OAuth 2.0 Credentials
1. Go to **APIs & Services** $\rightarrow$ **Credentials** $\rightarrow$ **Create Credentials** $\rightarrow$ **OAuth client ID**.
2. Application type: **Web application** (or Desktop app).
3. Set Authorized redirect URIs: `http://localhost:5000/oauth2callback`.
4. Download the JSON credentials file and obtain:
   - `Client ID`
   - `Client Secret`
   - `Refresh Token`

### Configure EasyMark
In `ai-service/.env`:
```env
GMAIL_CLIENT_ID="your_google_client_id.apps.googleusercontent.com"
GMAIL_CLIENT_SECRET="your_google_client_secret"
GMAIL_REFRESH_TOKEN="your_google_refresh_token"
```

---

## 5. Verifying Integration Status

1. **Via Frontend Dashboard**:
   - Open `http://localhost:5173`.
   - Click the **Settings** button in the header.
   - The **Enterprise Integrations & Settings** drawer displays real-time connection status for each connected system.
2. **Via Automated E2E Test Suite**:
   ```powershell
   node scripts/e2e_full_system_test.js
   ```
   Runs 18 end-to-end integration probes validating downstream FastAPI, upstream Express, MCP tools, and SSE token streaming.
