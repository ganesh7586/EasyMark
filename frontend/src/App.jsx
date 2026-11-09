import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ExecutionTraceModal from './components/ExecutionTraceModal';
import { queryAgent, getThreadHistory, deleteThread, getGatewayHealth } from './services/api';
import { 
  Sparkles, 
  Layers, 
  BookOpen, 
  Briefcase, 
  FileCode, 
  Mail, 
  ShieldCheck, 
  Bot, 
  Loader2,
  AlertCircle
} from 'lucide-react';

export default function App() {
  const [threads, setThreads] = useState(() => {
    try {
      const saved = localStorage.getItem('easymark_threads');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [currentThreadId, setCurrentThreadId] = useState(() => {
    return `session_${Date.now()}`;
  });

  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState('healthy');
  const [traceModalOpen, setTraceModalOpen] = useState(false);
  const [selectedTraceData, setSelectedTraceData] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Persist threads in localStorage
  useEffect(() => {
    try {
      localStorage.setItem('easymark_threads', JSON.stringify(threads));
    } catch (e) {
      console.warn('Failed to save threads to localStorage', e);
    }
  }, [threads]);

  // Initial gateway health check
  useEffect(() => {
    getGatewayHealth()
      .then((res) => {
        if (res && res.status) {
          setHealthStatus(res.status);
        }
      })
      .catch(() => {
        // Express gateway may be offline in dev if not yet started
        setHealthStatus('standby');
      });
  }, []);

  // Switch or start new thread
  const handleNewChat = () => {
    const newId = `session_${Date.now()}`;
    setCurrentThreadId(newId);
    setMessages([]);
    setErrorMessage(null);
  };

  const handleSelectThread = async (threadId) => {
    setCurrentThreadId(threadId);
    setErrorMessage(null);
    try {
      // Try fetching checkpointed history from backend
      const res = await getThreadHistory(threadId);
      const historyList = res?.data?.history || res?.history;
      if (res && res.success && Array.isArray(historyList)) {
        const loadedMessages = historyList.map((turn, i) => {
          if (turn.role === 'user') {
            return {
              id: `user_${i}`,
              role: 'user',
              content: turn.content || turn.query,
              timestamp: turn.timestamp || new Date().toISOString(),
            };
          } else {
            return {
              id: `agent_${i}`,
              role: 'assistant',
              content: turn.content || turn.response,
              citations: turn.citations || [],
              grounding_confidence: turn.grounding_confidence,
              routing_decision: turn.routing_decision,
              resolved_query: turn.resolved_query,
              original_query: turn.original_query,
              execution_trace: turn.execution_trace,
              latency_ms: turn.latency_ms,
              timestamp: turn.timestamp || new Date().toISOString(),
            };
          }
        });
        setMessages(loadedMessages);
      } else {
        // If no server history found, check local cache
        const localThread = threads.find((t) => t.id === threadId);
        if (localThread && localThread.messages) {
          setMessages(localThread.messages);
        } else {
          setMessages([]);
        }
      }
    } catch (err) {
      console.warn('Could not load remote thread history, checking local', err);
      const localThread = threads.find((t) => t.id === threadId);
      setMessages(localThread?.messages || []);
    }
  };

  const handleDeleteThread = async (threadId) => {
    try {
      await deleteThread(threadId);
    } catch (e) {
      // Ignore network errors on delete
    }
    const updated = threads.filter((t) => t.id !== threadId);
    setThreads(updated);
    if (currentThreadId === threadId) {
      handleNewChat();
    }
  };

  // Send query to LangGraph Agent via Express Gateway
  const handleSendMessage = async (queryText) => {
    if (!queryText.trim() || isLoading) return;
    setErrorMessage(null);

    const userMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: queryText,
      timestamp: new Date().toISOString(),
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const response = await queryAgent(queryText, currentThreadId, 'employee_default');

      if (response && response.success) {
        const payload = response.data || response;
        const assistantMessage = {
          id: `asst_${Date.now()}`,
          role: 'assistant',
          content: payload.response || payload.answer || 'Execution complete.',
          citations: payload.citations || [],
          grounding_confidence: payload.grounding_confidence,
          routing_decision: payload.routing_decision || payload.route || payload.evaluation?.routing,
          resolved_query: payload.resolved_query,
          original_query: queryText,
          execution_trace: payload.execution_trace || payload.trace,
          latency_ms: payload.latency_ms,
          timestamp: new Date().toISOString(),
        };

        const updatedHistory = [...newMessages, assistantMessage];
        setMessages(updatedHistory);

        // Update threads list
        setThreads((prev) => {
          const title = queryText.length > 36 ? `${queryText.substring(0, 36)}...` : queryText;
          const existing = prev.find((t) => t.id === currentThreadId);
          if (existing) {
            return prev.map((t) =>
              t.id === currentThreadId
                ? { ...t, turnsCount: updatedHistory.length, messages: updatedHistory }
                : t
            );
          } else {
            return [
              {
                id: currentThreadId,
                title,
                turnsCount: updatedHistory.length,
                messages: updatedHistory,
                createdAt: new Date().toISOString(),
              },
              ...prev,
            ];
          }
        });
      } else {
        throw new Error(response?.error || 'Unknown error occurred while contacting agent');
      }
    } catch (err) {
      console.error('Agent query error:', err);
      const errMsg = err.response?.data?.error || err.message || 'Failed to reach agent service';
      setErrorMessage(errMsg);

      const errorReply = {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `**Error communicating with Agent Gateway**: ${errMsg}\n\nPlease verify that the backend Gateway (Port 5000) and AI Service (Port 8000) are running.`,
        routing_decision: 'error',
        grounding_confidence: 0,
        timestamp: new Date().toISOString(),
      };
      setMessages([...newMessages, errorReply]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenTrace = (message) => {
    setSelectedTraceData({
      trace: message.execution_trace,
      metadata: {
        routing_decision: message.routing_decision,
        grounding_confidence: message.grounding_confidence,
        latency_ms: message.latency_ms,
        resolved_query: message.resolved_query,
        original_query: message.original_query,
      },
    });
    setTraceModalOpen(true);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      {/* Sidebar with Sessions & Sources */}
      <Sidebar
        threads={threads}
        currentThreadId={currentThreadId}
        onSelectThread={handleSelectThread}
        onDeleteThread={handleDeleteThread}
      />

      {/* Main Chat Viewport */}
      <div className="flex flex-col flex-1 h-full min-w-0">
        <Header
          threadId={currentThreadId}
          onNewChat={handleNewChat}
          healthStatus={healthStatus}
          toolsCount={15}
        />

        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          <div className="max-w-4xl mx-auto">
            {messages.length === 0 ? (
              /* Welcome Hero */
              <div className="py-12 text-center max-w-2xl mx-auto space-y-6">
                <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-sky-600 via-sky-500 to-indigo-600 flex items-center justify-center mx-auto shadow-2xl shadow-sky-500/25">
                  <Bot className="w-8 h-8 text-white" />
                </div>

                <div className="space-y-2">
                  <h2 className="text-2xl font-bold tracking-tight text-white">
                    EasyMark Enterprise Knowledge Intelligence
                  </h2>
                  <p className="text-sm text-slate-400 max-w-lg mx-auto">
                    Hybrid Question Answering powered by LangGraph StateGraph, MongoDB Vector RAG, and Live Model Context Protocol (MCP) bridges.
                  </p>
                </div>

                {/* Architecture Feature Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left pt-4">
                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
                    <div className="flex items-center space-x-2.5 mb-1.5">
                      <BookOpen className="w-4 h-4 text-sky-400" />
                      <h3 className="font-semibold text-white text-xs">Static Policy RAG</h3>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Company handbooks, remote work policies, compliance PDFs with cosine similarity vector retrieval.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
                    <div className="flex items-center space-x-2.5 mb-1.5">
                      <Briefcase className="w-4 h-4 text-blue-400" />
                      <h3 className="font-semibold text-white text-xs">Jira Project Cloud</h3>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Real-time blocker tickets, sprint backlogs, release milestones, and active SEV-1 incident queries.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
                    <div className="flex items-center space-x-2.5 mb-1.5">
                      <FileCode className="w-4 h-4 text-amber-400" />
                      <h3 className="font-semibold text-white text-xs">Notion Workspace</h3>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Live PRDs, engineering design specs, architecture documents, and weekly sync minutes.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
                    <div className="flex items-center space-x-2.5 mb-1.5">
                      <Mail className="w-4 h-4 text-rose-400" />
                      <h3 className="font-semibold text-white text-xs">Google Workspace</h3>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Executive approvals, unread email escalations, leadership updates, and internal communications.
                    </p>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800/80 text-xs text-slate-400 flex items-center justify-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Stateful Multi-Turn Memory with Pronoun Coreference Resolution</span>
                </div>
              </div>
            ) : (
              /* Message List */
              messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onOpenTrace={() => handleOpenTrace(msg)}
                />
              ))
            )}

            {/* Agent Thinking Indicator */}
            {isLoading && (
              <div className="flex items-start space-x-3 mb-6 animate-pulse">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white flex-shrink-0 shadow-md">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-4 rounded-2xl rounded-tl-sm bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-center space-x-3">
                  <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                  <span>Evaluating query router, checking memory & searching live knowledge sources...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Chat Input Bar */}
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>

      {/* Execution Trace Inspection Modal */}
      {selectedTraceData && (
        <ExecutionTraceModal
          isOpen={traceModalOpen}
          onClose={() => setTraceModalOpen(false)}
          trace={selectedTraceData.trace}
          metadata={selectedTraceData.metadata}
        />
      )}
    </div>
  );
}
