import React, { useState, useEffect } from 'react';
import { 
  X, 
  UploadCloud, 
  FileText, 
  Trash2, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Layers,
  Database,
  RefreshCw
} from 'lucide-react';
import { getDocuments, uploadDocument, deleteDocument } from '../services/api';

export default function UploadModal({ isOpen, onClose, onDocumentUpdated }) {
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [message, setMessage] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadDocuments();
    }
  }, [isOpen]);

  const loadDocuments = async () => {
    setIsLoadingList(true);
    try {
      const res = await getDocuments();
      if (res && res.success && Array.isArray(res.data)) {
        setDocuments(res.data);
      }
    } catch (err) {
      console.warn('Failed to load documents', err);
    } finally {
      setIsLoadingList(false);
    }
  };

  if (!isOpen) return null;

  const handleFileUpload = async (file) => {
    if (!file) return;
    setIsUploading(true);
    setMessage(null);

    const isPdf = file.name.toLowerCase().endsWith('.pdf');
    const reader = new FileReader();

    reader.onload = async (e) => {
      try {
        let res;
        if (isPdf) {
          // Convert Data URL (data:application/pdf;base64,...) to pure base64
          const dataUrl = e.target.result;
          const base64Content = dataUrl.split(',')[1];
          res = await uploadDocument(file.name, base64Content, null);
        } else {
          // Text / Markdown
          const textContent = e.target.result;
          res = await uploadDocument(file.name, null, textContent);
        }

        if (res && res.success) {
          setMessage({
            type: 'success',
            text: `Successfully ingested "${file.name}" (${res.data?.total_chunks || 0} vector chunks indexed).`,
          });
          loadDocuments();
          if (onDocumentUpdated) onDocumentUpdated();
        } else {
          throw new Error(res?.error || 'Ingestion failed');
        }
      } catch (err) {
        setMessage({
          type: 'error',
          text: err.response?.data?.error || err.message || 'Failed to upload document',
        });
      } finally {
        setIsUploading(false);
      }
    };

    if (isPdf) {
      reader.readAsDataURL(file);
    } else {
      reader.readAsText(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDelete = async (docName) => {
    try {
      await deleteDocument(docName);
      loadDocuments();
      if (onDocumentUpdated) onDocumentUpdated();
    } catch (err) {
      console.error('Delete document failed', err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl shadow-sky-950/40 animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">Dynamic Knowledge Ingestion</h2>
              <p className="text-xs text-slate-400">Upload PDFs, Markdown & Policies directly into Vector Store</p>
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
          
          {/* Drag & Drop Upload Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-6 text-center transition-all ${
              dragActive
                ? 'border-sky-500 bg-sky-500/10'
                : 'border-slate-800 bg-slate-950/40 hover:border-slate-700'
            }`}
          >
            <UploadCloud className="w-10 h-10 text-sky-400 mx-auto mb-2" />
            <div className="text-sm font-semibold text-slate-200">
              Drag and drop policy documents here
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Supports <strong className="text-slate-300">.pdf</strong>, <strong className="text-slate-300">.md</strong>, and <strong className="text-slate-300">.txt</strong> files
            </p>

            <label className="mt-4 inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium cursor-pointer transition-colors shadow-md shadow-sky-600/20">
              <span>Choose Document</span>
              <input
                type="file"
                accept=".pdf,.txt,.md"
                className="hidden"
                disabled={isUploading}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />
            </label>
          </div>

          {/* Upload Status Banner */}
          {isUploading && (
            <div className="p-3 rounded-xl bg-sky-950/40 border border-sky-800/40 text-sky-300 flex items-center space-x-2.5">
              <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
              <span>Extracting text, generating 384-D neural embeddings & indexing...</span>
            </div>
          )}

          {message && (
            <div className={`p-3 rounded-xl border flex items-center space-x-2.5 ${
              message.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-300'
                : 'bg-rose-950/40 border-rose-800/40 text-rose-300'
            }`}>
              {message.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />}
              <span>{message.text}</span>
            </div>
          )}

          {/* Currently Indexed Documents List */}
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                <span>Indexed Documents in Vector Store ({documents.length})</span>
              </h3>
              <button
                onClick={loadDocuments}
                className="text-[11px] text-slate-400 hover:text-white flex items-center space-x-1"
                title="Refresh list"
              >
                <RefreshCw className={`w-3 h-3 ${isLoadingList ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>

            <div className="space-y-2">
              {documents.length === 0 ? (
                <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-slate-500">
                  No documents found in registry.
                </div>
              ) : (
                documents.map((doc, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl border border-slate-800 bg-slate-950/60 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-3 truncate">
                      <FileText className="w-4 h-4 text-sky-400 flex-shrink-0" />
                      <div className="truncate">
                        <div className="font-medium text-slate-200 truncate">{doc.doc_name}</div>
                        <div className="text-[10px] text-slate-500 flex items-center space-x-2 mt-0.5">
                          <span>{doc.total_pages} page(s)</span>
                          <span>•</span>
                          <span className="text-sky-400 font-mono">{doc.chunk_count} vector chunks</span>
                          {doc.ingested_at && (
                            <>
                              <span>•</span>
                              <span>{new Date(doc.ingested_at).toLocaleDateString()}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDelete(doc.doc_name)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors flex-shrink-0"
                      title="Purge document"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            Real-time Vector Search Ingestion Pipeline
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
