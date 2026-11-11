import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Loader2, 
  BookOpen, 
  Briefcase, 
  FileCode, 
  Mail,
  Zap,
  Mic,
  MicOff
} from 'lucide-react';

export default function ChatInput({ onSendMessage, isLoading }) {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);

  // Setup Web Speech API for voice input
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
        setIsListening(false);
      };

      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        setIsListening(false);
      }
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const quickPrompts = [
    {
      label: 'Policy RAG: Remote Work Guidelines',
      icon: <BookOpen className="w-3 h-3 text-sky-400" />,
      query: 'What are the company policies regarding remote work equipment and core working hours?',
    },
    {
      label: 'Jira: Sprint Blocker Issues',
      icon: <Briefcase className="w-3 h-3 text-blue-400" />,
      query: 'What blocker issues are currently open in the active sprint in Jira?',
    },
    {
      label: 'Notion: Engineering Architecture',
      icon: <FileCode className="w-3 h-3 text-amber-400" />,
      query: 'Search Notion for the latest system architecture specification and onboarding notes.',
    },
    {
      label: 'Gmail: Urgent VP Escalations',
      icon: <Mail className="w-3 h-3 text-rose-400" />,
      query: 'Are there any urgent escalations or unread priority messages in Gmail today?',
    },
  ];

  return (
    <div className="border-t border-slate-800 bg-slate-900/90 backdrop-blur p-4">
      <div className="max-w-4xl mx-auto space-y-3">
        {/* Quick Suggestion Pills */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-1 text-xs no-scrollbar">
          <span className="text-slate-500 font-semibold flex items-center space-x-1 flex-shrink-0">
            <Zap className="w-3 h-3 text-amber-400" />
            <span>Quick:</span>
          </span>
          {quickPrompts.map((item, idx) => (
            <button
              key={idx}
              onClick={() => onSendMessage(item.query)}
              disabled={isLoading}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-slate-800/80 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700/80 hover:border-slate-600 transition-all text-xs flex-shrink-0 disabled:opacity-50"
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        {/* Input Textarea & Send Button */}
        <form onSubmit={handleSubmit} className="relative flex items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? "Listening to your voice... Speak now." : "Ask anything across company policies, Jira blockers, Notion docs, and Gmail..."}
            rows={1}
            disabled={isLoading}
            className={`w-full pl-4 pr-24 py-3 bg-slate-950 border rounded-2xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition-all resize-none ${
              isListening ? 'border-rose-500 ring-1 ring-rose-500' : 'border-slate-800 focus:border-sky-500 focus:ring-1 focus:ring-sky-500'
            }`}
          />

          {/* Voice Input Button */}
          <button
            type="button"
            onClick={toggleListening}
            className={`absolute right-12 bottom-2.5 p-2 rounded-xl transition-all ${
              isListening
                ? 'bg-rose-600 text-white animate-pulse shadow-md shadow-rose-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
            title={isListening ? 'Listening (Click to stop)' : 'Click to speak'}
          >
            <Mic className="w-4 h-4" />
          </button>

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2.5 bottom-2.5 p-2 rounded-xl bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 text-white disabled:text-slate-600 transition-all shadow-md shadow-sky-600/20 disabled:shadow-none"
            title="Send query (Enter)"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-sky-300" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>

        <div className="flex items-center justify-between text-[11px] text-slate-500 px-1">
          <span>Press <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[10px]">Shift+Enter</kbd> for newline</span>
          <span className="font-mono">LangGraph StateGraph Router v1.0</span>
        </div>
      </div>
    </div>
  );
}
