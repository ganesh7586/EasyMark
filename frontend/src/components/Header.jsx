import React from 'react';
import { 
  Sparkles, 
  Layers, 
  PlusCircle, 
  ShieldCheck, 
  Activity, 
  Database,
  ExternalLink,
  Settings
} from 'lucide-react';

export default function Header({ 
  threadId, 
  onNewChat, 
  healthStatus, 
  toolsCount = 15,
  onOpenTrace,
  onOpenSettings
}) {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 flex items-center justify-between z-10">
      {/* Brand & Subtitle */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 via-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-lg text-white tracking-tight">EasyMark</h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
              LangGraph Agent v1.0
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Enterprise Intelligence • Static Policy RAG & Live MCP Systems
          </p>
        </div>
      </div>

      {/* Center Status Indicators */}
      <div className="hidden md:flex items-center space-x-4 text-xs">
        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <Database className="w-3.5 h-3.5 text-emerald-400" />
          <span>MongoDB Atlas:</span>
          <span className="text-emerald-400 font-medium">384-D Vector Index</span>
        </div>

        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <Layers className="w-3.5 h-3.5 text-sky-400" />
          <span>MCP Tools:</span>
          <span className="text-sky-400 font-medium">{toolsCount} Live Tools</span>
        </div>

        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>Security:</span>
          <span className="text-indigo-400 font-medium">HMAC Bridge Validated</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center space-x-2.5">
        <button
          onClick={onOpenSettings}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium border border-slate-700/80 transition-colors"
          title="Integrations & Settings"
        >
          <Settings className="w-3.5 h-3.5 text-slate-400" />
          <span>Settings</span>
        </button>

        <button
          onClick={onNewChat}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium shadow-md shadow-sky-600/20 transition-all duration-150 active:scale-95"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Thread</span>
        </button>
      </div>
    </header>
  );
}
