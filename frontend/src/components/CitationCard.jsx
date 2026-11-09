import React, { useState } from 'react';
import { 
  FileText, 
  ExternalLink, 
  Briefcase, 
  FileCode, 
  Mail, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp,
  Percent,
  Layers
} from 'lucide-react';

export default function CitationCard({ citations = [], groundingConfidence = null }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!citations || citations.length === 0) {
    return null;
  }

  const getSourceIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'jira':
        return <Briefcase className="w-3.5 h-3.5 text-blue-400" />;
      case 'notion':
        return <FileCode className="w-3.5 h-3.5 text-amber-400" />;
      case 'gmail':
        return <Mail className="w-3.5 h-3.5 text-rose-400" />;
      case 'pdf':
      case 'policy':
      default:
        return <FileText className="w-3.5 h-3.5 text-sky-400" />;
    }
  };

  const getSourceBadge = (type) => {
    switch (type?.toLowerCase()) {
      case 'jira':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'notion':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'gmail':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'pdf':
      case 'policy':
      default:
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
    }
  };

  return (
    <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden text-xs">
      {/* Header bar toggler */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3.5 py-2.5 flex items-center justify-between text-left hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-sky-400" />
          <span className="font-semibold text-slate-200">
            Grounding Citations ({citations.length} Verified Sources)
          </span>
          {groundingConfidence !== null && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>{(groundingConfidence * 100).toFixed(1)}% Provenance Grounded</span>
            </span>
          )}
        </div>
        <div className="flex items-center space-x-1 text-slate-400">
          <span className="text-[11px]">{isOpen ? 'Collapse' : 'Inspect Sources'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Sources Grid */}
      {isOpen && (
        <div className="p-3 border-t border-slate-800/80 space-y-2 bg-slate-950/40">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {citations.map((cite, idx) => {
              // Handle string or object citation
              const isObj = typeof cite === 'object' && cite !== null;
              const sourceType = isObj ? (cite.source_type || cite.type || 'policy') : 'policy';
              const title = isObj ? (cite.document_name || cite.key || cite.title || cite.subject || cite.source || `Citation #${idx + 1}`) : cite;
              const subtitle = isObj ? (cite.section || cite.status || cite.from || cite.page_id || '') : '';
              const snippet = isObj ? (cite.snippet || cite.text || cite.content || cite.summary || '') : '';
              const score = isObj && cite.score !== undefined ? cite.score : null;

              return (
                <div 
                  key={idx}
                  className="p-3 rounded-lg border border-slate-800 bg-slate-900/80 hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center space-x-1.5 font-medium text-slate-200 truncate">
                        {getSourceIcon(sourceType)}
                        <span className="truncate">{title}</span>
                      </div>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border uppercase tracking-wider ${getSourceBadge(sourceType)}`}>
                        {sourceType}
                      </span>
                    </div>

                    {subtitle && (
                      <div className="text-[11px] text-slate-400 mb-1.5 font-medium">
                        {subtitle}
                      </div>
                    )}

                    {snippet && (
                      <p className="text-[11px] text-slate-400 line-clamp-3 italic bg-slate-950/50 p-2 rounded border border-slate-800/50">
                        "{snippet}"
                      </p>
                    )}
                  </div>

                  {score !== null && (
                    <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>Vector Relevance</span>
                      <span className="text-sky-400 font-semibold">{(score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
