import React from 'react';
import { 
  X, 
  Activity, 
  Clock, 
  GitBranch, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle,
  ArrowRight,
  Code
} from 'lucide-react';

export default function ExecutionTraceModal({ isOpen, onClose, trace, metadata }) {
  if (!isOpen) return null;

  const steps = Array.isArray(trace) ? trace : (trace?.steps || []);
  const routingDecision = metadata?.routing_decision || trace?.routing_decision || 'N/A';
  const totalLatency = metadata?.latency_ms || trace?.latency_ms || null;
  const confidence = metadata?.grounding_confidence ?? trace?.grounding_confidence ?? null;

  const getStepColor = (stepName) => {
    if (stepName?.includes('route') || stepName?.includes('eval')) return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
    if (stepName?.includes('rag') || stepName?.includes('static')) return 'text-sky-400 bg-sky-500/10 border-sky-500/30';
    if (stepName?.includes('mcp') || stepName?.includes('tool')) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    if (stepName?.includes('validator') || stepName?.includes('evidence')) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    return 'text-slate-400 bg-slate-800 border-slate-700';
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl shadow-sky-950/40 animate-in fade-in zoom-in-95 duration-150">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">LangGraph Execution Trace</h2>
              <p className="text-xs text-slate-400">Autonomous Agent Workflow & Node State Transitions</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Trace Top Metrics */}
        <div className="px-6 py-3.5 bg-slate-950/60 border-b border-slate-800 grid grid-cols-3 gap-3 text-xs">
          <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Router Path</div>
            <div className="font-mono font-bold text-sky-400 mt-0.5 truncate">{routingDecision}</div>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Total Graph Latency</div>
            <div className="font-mono font-bold text-slate-200 mt-0.5">
              {totalLatency ? `${totalLatency.toFixed(1)} ms` : 'Sub-second'}
            </div>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Citation Grounding</div>
            <div className="font-mono font-bold text-emerald-400 mt-0.5">
              {confidence !== null ? `${(confidence * 100).toFixed(1)}%` : 'Grounded'}
            </div>
          </div>
        </div>

        {/* Modal Body: Steps & Raw Payload */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1 text-xs">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-1.5">
              <GitBranch className="w-3.5 h-3.5 text-sky-400" />
              <span>Node Execution Pipeline ({steps.length} Nodes)</span>
            </h3>

            {steps.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-slate-500">
                Direct synthesis trace (single pass).
              </div>
            ) : (
              <div className="space-y-2.5">
                {steps.map((st, i) => {
                  const stepName = typeof st === 'string' ? st : (st.step || st.node || `Step ${i + 1}`);
                  const duration = st.duration_ms || st.latency_ms;
                  return (
                    <div 
                      key={i}
                      className="p-3 rounded-xl border border-slate-800 bg-slate-950/40 flex items-start justify-between"
                    >
                      <div className="flex items-center space-x-3">
                        <span className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-mono text-[11px] text-slate-400">
                          {i + 1}
                        </span>
                        <div>
                          <span className={`px-2 py-0.5 rounded font-mono text-xs border ${getStepColor(stepName)}`}>
                            {stepName}
                          </span>
                          {st.details && (
                            <div className="mt-1 text-[11px] text-slate-400">
                              {typeof st.details === 'string' ? st.details : JSON.stringify(st.details)}
                            </div>
                          )}
                        </div>
                      </div>

                      {duration && (
                        <div className="flex items-center space-x-1 text-slate-400 font-mono text-[11px]">
                          <Clock className="w-3 h-3 text-slate-500" />
                          <span>{duration.toFixed(1)}ms</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Raw JSON Trace Viewer */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center space-x-1.5">
              <Code className="w-3.5 h-3.5 text-indigo-400" />
              <span>Diagnostic Metadata Payload</span>
            </h3>
            <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-56 leading-relaxed">
              {JSON.stringify({ trace, metadata }, null, 2)}
            </pre>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            LangGraph StateGraph Engine • Deterministic Execution
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close Trace
          </button>
        </div>

      </div>
    </div>
  );
}
