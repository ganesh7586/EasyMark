import React, { useState } from 'react';
import { 
  X, 
  Settings, 
  Key, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink, 
  Briefcase, 
  FileCode, 
  Mail, 
  Sparkles, 
  Database,
  Radio,
  HelpCircle
} from 'lucide-react';

export default function SettingsModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl shadow-sky-950/40 animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">Enterprise Integrations & Settings</h2>
              <p className="text-xs text-slate-400">Live Cloud APIs, Simulated Fixtures & Security Architecture</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs flex-1">
          
          {/* Operational Architecture Banner */}
          <div className="p-3.5 rounded-xl bg-sky-950/40 border border-sky-800/50 flex items-start space-x-3 text-sky-200">
            <Radio className="w-4 h-4 text-sky-400 flex-shrink-0 mt-0.5 animate-pulse" />
            <div>
              <div className="font-semibold text-xs text-white">Dual-Mode Architecture Active</div>
              <div className="text-[11px] text-sky-300/90 mt-0.5 leading-relaxed">
                EasyMark automatically switches between <strong>Live Cloud REST APIs</strong> (when API tokens are configured in <code className="bg-sky-900/60 px-1 py-0.5 rounded font-mono">.env</code>) and <strong>Deterministic Enterprise Fixtures</strong> (Project Alpha SLA dataset) when running offline or without credentials.
              </div>
            </div>
          </div>

          {/* Integration Status Cards */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Key className="w-3.5 h-3.5 text-indigo-400" />
              <span>Connected Knowledge Systems</span>
            </h3>

            {/* Groq Cloud */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/50 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-200 text-xs">Groq Cloud LLM (Llama 3.3 70B)</div>
                  <div className="text-[11px] text-slate-400">Ultra-fast inference & Server-Sent Events (SSE) streaming</div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Ready / Streaming
              </span>
            </div>

            {/* Jira Cloud */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/50 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
                  <Briefcase className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-200 text-xs">Atlassian Jira Cloud REST API</div>
                  <div className="text-[11px] text-slate-400">
                    Env: <code className="font-mono text-slate-300">JIRA_BASE_URL</code>, <code className="font-mono text-slate-300">JIRA_EMAIL</code>, <code className="font-mono text-slate-300">JIRA_API_TOKEN</code>
                  </div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-500/10 text-sky-400 border border-sky-500/20">
                Dual-Mode Supported
              </span>
            </div>

            {/* Notion */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/50 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <FileCode className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-200 text-xs">Notion Workspace API v1</div>
                  <div className="text-[11px] text-slate-400">
                    Env: <code className="font-mono text-slate-300">NOTION_API_KEY</code>, <code className="font-mono text-slate-300">NOTION_DATABASE_ID</code>
                  </div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-500/10 text-sky-400 border border-sky-500/20">
                Dual-Mode Supported
              </span>
            </div>

            {/* Gmail */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/50 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-200 text-xs">Google Workspace Gmail API</div>
                  <div className="text-[11px] text-slate-400">
                    Env: <code className="font-mono text-slate-300">GMAIL_CLIENT_ID</code>, <code className="font-mono text-slate-300">GMAIL_REFRESH_TOKEN</code>
                  </div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-500/10 text-sky-400 border border-sky-500/20">
                Dual-Mode Supported
              </span>
            </div>

            {/* MongoDB Atlas */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/50 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Database className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-200 text-xs">MongoDB Atlas Vector Search</div>
                  <div className="text-[11px] text-slate-400">384-D dense embeddings (all-MiniLM-L6-v2) + state checkpoints</div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Connected
              </span>
            </div>
          </div>

          {/* Quick Setup Instructions Callout */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center space-x-1.5 text-slate-300 font-semibold">
              <HelpCircle className="w-3.5 h-3.5 text-sky-400" />
              <span>How to switch to Live Real-Time APIs:</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Open <code className="text-sky-300 font-mono">ai-service/.env</code> and supply your free Atlassian API token, Notion secret, or Google OAuth credentials. See the complete step-by-step documentation in <code className="text-sky-300 font-mono">docs/LIVE_API_SETUP_GUIDE.md</code>.
            </p>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            EasyMark Dual-Mode MCP Engine v1.0
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close Settings
          </button>
        </div>

      </div>
    </div>
  );
}
