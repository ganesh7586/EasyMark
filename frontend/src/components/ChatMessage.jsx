import React from 'react';
import { 
  User, 
  Sparkles, 
  Layers, 
  CheckCircle2, 
  AlertCircle, 
  Activity, 
  Clock, 
  Copy, 
  Check, 
  Bot,
  Compass,
  Volume2,
  VolumeX
} from 'lucide-react';
import CitationCard from './CitationCard';

export default function ChatMessage({ message, onOpenTrace }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);

  const toggleSpeak = () => {
    if (!window.speechSynthesis) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(message.content);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
      setIsSpeaking(true);
    }
  };

  const handleCopy = () => {
    if (message.content) {
      navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getRouterBadge = (decision) => {
    switch (decision?.toLowerCase()) {
      case 'static_rag':
        return { label: 'Static Policy RAG', color: 'bg-sky-500/10 text-sky-400 border-sky-500/20' };
      case 'mcp_live':
        return { label: 'Live Enterprise MCP', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20' };
      case 'hybrid':
        return { label: 'Hybrid RAG + MCP', color: 'bg-purple-500/10 text-purple-400 border-purple-500/20' };
      case 'direct_llm':
        return { label: 'Direct Synthesis', color: 'bg-slate-500/10 text-slate-400 border-slate-500/20' };
      default:
        return { label: decision || 'Autonomous Route', color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' };
    }
  };

  const badgeInfo = getRouterBadge(message.routing_decision);

  // Markdown-like light formatting for paragraphs, bold, inline code, and lists
  const formatContent = (text) => {
    if (!text) return null;
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      // Headers
      if (line.startsWith('### ')) {
        return <h4 key={idx} className="text-sm font-bold text-white mt-3 mb-1">{line.replace('### ', '')}</h4>;
      }
      if (line.startsWith('## ')) {
        return <h3 key={idx} className="text-base font-bold text-white mt-4 mb-2">{line.replace('## ', '')}</h3>;
      }
      if (line.startsWith('# ')) {
        return <h2 key={idx} className="text-lg font-bold text-white mt-4 mb-2">{line.replace('# ', '')}</h2>;
      }
      // Bullet list items
      if (line.startsWith('- ') || line.startsWith('* ')) {
        const bulletText = line.substring(2);
        return (
          <li key={idx} className="ml-4 list-disc text-slate-300 my-1 leading-relaxed">
            {renderInline(bulletText)}
          </li>
        );
      }
      // Blank lines
      if (!line.trim()) {
        return <div key={idx} className="h-2" />;
      }
      // Standard paragraph
      return (
        <p key={idx} className="text-slate-300 leading-relaxed my-1">
          {renderInline(line)}
        </p>
      );
    });
  };

  // Helper for inline bold, code backticks
  const renderInline = (str) => {
    const parts = str.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 font-mono text-[11px] border border-slate-700/60">
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-white">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-6">
        <div className="flex items-start space-x-3 max-w-2xl">
          <div className="bg-sky-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-md text-sm leading-relaxed">
            <p className="whitespace-pre-wrap">{message.content}</p>
            <div className="mt-1 text-[10px] text-sky-200 text-right opacity-80">
              {message.timestamp ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}
            </div>
          </div>
          <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 flex-shrink-0 shadow-sm">
            <User className="w-4 h-4" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-6">
      <div className="flex items-start space-x-3 max-w-3xl w-full">
        {/* Agent Avatar */}
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white flex-shrink-0 shadow-md shadow-sky-600/20">
          <Bot className="w-4 h-4" />
        </div>

        {/* Assistant Content Box */}
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm shadow-lg">
          {/* Header Row: Routing Badge & Grounding Pill */}
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-800/80 text-xs">
            <div className="flex items-center space-x-2">
              <span className={`px-2.5 py-0.5 rounded-full font-medium border flex items-center space-x-1.5 ${badgeInfo.color}`}>
                <Compass className="w-3 h-3" />
                <span>{badgeInfo.label}</span>
              </span>

              {message.grounding_confidence !== undefined && message.grounding_confidence !== null && (
                <span className={`px-2 py-0.5 rounded-full font-mono text-[11px] border flex items-center space-x-1 ${
                  message.grounding_confidence >= 0.70 
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                }`}>
                  <CheckCircle2 className="w-3 h-3" />
                  <span>{(message.grounding_confidence * 100).toFixed(0)}% Grounded</span>
                </span>
              )}
            </div>

            {/* Trace Inspection Trigger */}
            <div className="flex items-center space-x-2">
              {message.execution_trace && (
                <button
                  onClick={() => onOpenTrace && onOpenTrace(message)}
                  className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition-colors"
                >
                  <Activity className="w-3 h-3 text-sky-400" />
                  <span>Inspect Trace</span>
                </button>
              )}

              <button
                onClick={toggleSpeak}
                className={`p-1 rounded-md transition-colors ${
                  isSpeaking ? 'text-sky-400 bg-sky-500/10' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
                title={isSpeaking ? 'Stop speaking' : 'Listen to answer'}
              >
                {isSpeaking ? <VolumeX className="w-3.5 h-3.5 text-sky-400 animate-pulse" /> : <Volume2 className="w-3.5 h-3.5" />}
              </button>

              <button
                onClick={handleCopy}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                title="Copy response"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Pronoun Coreference Resolution Notice */}
          {message.resolved_query && message.original_query && message.resolved_query !== message.original_query && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-sky-950/40 border border-sky-800/40 text-[11px] text-sky-300 flex items-center space-x-2">
              <span className="font-semibold uppercase text-sky-400">Resolved Pronoun:</span>
              <span className="italic">"{message.original_query}"</span>
              <span>→</span>
              <span className="font-medium text-white">"{message.resolved_query}"</span>
            </div>
          )}

          {/* Markdown / Body Content */}
          <div className="prose prose-invert max-w-none text-slate-200 text-sm">
            {formatContent(message.content)}
            {message.isStreaming && (
              <span className="inline-block w-1.5 h-4 ml-1 bg-sky-400 animate-pulse rounded-sm align-middle" />
            )}
          </div>

          {/* Structured Provenance Citations */}
          {message.citations && message.citations.length > 0 && (
            <CitationCard 
              citations={message.citations} 
              groundingConfidence={message.grounding_confidence}
            />
          )}

          {/* Timestamp & Latency Footer */}
          <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <div className="flex items-center space-x-1">
              <Clock className="w-2.5 h-2.5" />
              <span>
                {message.latency_ms ? `${(message.latency_ms / 1000).toFixed(2)}s generation latency` : 'Realtime'}
              </span>
            </div>
            <span>
              {message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : ''}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
