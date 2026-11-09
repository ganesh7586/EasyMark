import React from 'react';
import { 
  MessageSquare, 
  Trash2, 
  FileText, 
  CheckCircle2, 
  ExternalLink,
  BookOpen,
  Briefcase,
  FileCode,
  Mail,
  Zap,
  Clock
} from 'lucide-react';

export default function Sidebar({
  threads,
  currentThreadId,
  onSelectThread,
  onDeleteThread,
  liveChannels,
  onQuickPrompt
}) {
  return (
    <aside className="w-80 border-r border-slate-800 bg-slate-900/50 flex flex-col h-full overflow-hidden">
      {/* Session Threads Section */}
      <div className="p-4 border-b border-slate-800 flex-1 overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Active Sessions ({threads.length})
          </span>
        </div>

        <div className="space-y-1.5">
          {threads.length === 0 ? (
            <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-xs text-slate-500">
              No previous threads. Send a query to start session tracking.
            </div>
          ) : (
            threads.map((t) => {
              const isActive = t.id === currentThreadId;
              return (
                <div
                  key={t.id}
                  onClick={() => onSelectThread(t.id)}
                  className={`group px-3 py-2.5 rounded-xl cursor-pointer flex items-center justify-between text-xs transition-all ${
                    isActive
                      ? 'bg-sky-500/10 border border-sky-500/30 text-sky-200 shadow-sm'
                      : 'hover:bg-slate-800/60 border border-transparent text-slate-300'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 truncate">
                    <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? 'text-sky-400' : 'text-slate-500'}`} />
                    <div className="truncate">
                      <div className="font-medium truncate">{t.title || t.id}</div>
                      <div className="text-[10px] text-slate-500 flex items-center space-x-1">
                        <Clock className="w-2.5 h-2.5" />
                        <span>{t.turnsCount} turn(s)</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(t.id);
                    }}
                    title="Delete session"
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-rose-500/20 hover:text-rose-400 text-slate-500 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Integrated Live Knowledge Sources */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/60 space-y-3">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <span>Integrated Sources</span>
          <span className="text-[10px] text-emerald-400 font-mono">100% Operational</span>
        </span>

        <div className="space-y-2 text-xs">
          {/* Static RAG */}
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BookOpen className="w-3.5 h-3.5 text-sky-400" />
              <div>
                <div className="font-medium text-slate-200">Static Policy RAG</div>
                <div className="text-[10px] text-slate-500">3 PDFs • 24 Chunks • MiniLM</div>
              </div>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>

          {/* Jira */}
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Briefcase className="w-3.5 h-3.5 text-blue-400" />
              <div>
                <div className="font-medium text-slate-200">Atlassian Jira Cloud</div>
                <div className="text-[10px] text-slate-500">Blockers, Sprints & SEV-1</div>
              </div>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>

          {/* Notion */}
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileCode className="w-3.5 h-3.5 text-amber-400" />
              <div>
                <div className="font-medium text-slate-200">Notion Workspace</div>
                <div className="text-[10px] text-slate-500">PRDs, Specs & Sync Notes</div>
              </div>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>

          {/* Gmail */}
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Mail className="w-3.5 h-3.5 text-rose-400" />
              <div>
                <div className="font-medium text-slate-200">Google Workspace</div>
                <div className="text-[10px] text-slate-500">Escalations & Approvals</div>
              </div>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>
        </div>
      </div>
    </aside>
  );
}
