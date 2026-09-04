import React, { useState } from 'react';
import axios from 'axios';
import { Play, Loader2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const EXPLORER_BASE = 'https://amoy.polygonscan.com/tx/';

export default function TaskRunner() {
  const [prompt, setPrompt] = useState('write a Python function is_valid_email(s) that returns True if the input string is a properly formatted email address, False otherwise.');
  const [status, setStatus] = useState('idle'); // idle, running, success, error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const runTask = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    
    setStatus('running');
    setResult(null);
    setErrorMsg('');

    try {
      const response = await axios.post(`${API_BASE}/run_task`, {
        raw_request: prompt
      });
      setResult(response.data);
      setStatus('success');
    } catch (err) {
      console.error(err);
      setStatus('error');
      setErrorMsg(err.response?.data?.detail || err.message || 'An error occurred');
    }
  };

  const getStatusBadge = (finalStatus) => {
    switch (finalStatus) {
      case 'paid':
        return <span className="badge badge-green flex items-center gap-1"><CheckCircle size={12} /> PAID</span>;
      case 'refunded':
        return <span className="badge badge-red flex items-center gap-1"><XCircle size={12} /> REFUNDED</span>;
      case 'escalated':
        return <span className="badge badge-yellow flex items-center gap-1"><AlertTriangle size={12} /> ESCALATED</span>;
      default:
        return <span className="badge badge-blue">{finalStatus || 'UNKNOWN'}</span>;
    }
  };

  return (
    <div className="grid grid-cols-2 gap-6" style={{ gridTemplateColumns: '1fr 1fr' }}>
      {/* Left Column: Input Form */}
      <div>
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 className="mb-2">Run a Task</h2>
          <p className="text-muted text-sm mb-6">Submit a prompt. VadaChain will match an agent, lock funds in escrow, verify the output, and release/refund automatically.</p>
          
          <form onSubmit={runTask}>
            <div className="form-group">
              <label className="form-label">Task Request</label>
              <textarea 
                className="form-control" 
                rows={6}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. write a script to calculate fibonacci numbers..."
              />
            </div>
            
            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: '100%' }}
              disabled={status === 'running'}
            >
              {status === 'running' ? (
                <><Loader2 size={18} className="spinner" /> Executing Pipeline...</>
              ) : (
                <><Play size={18} /> Submit to VadaChain</>
              )}
            </button>
          </form>
          
          {status === 'error' && (
            <div className="mt-4" style={{ padding: '1rem', background: 'rgba(239,68,68,0.1)', borderLeft: '4px solid #ef4444', borderRadius: 4 }}>
              <strong style={{ color: '#ef4444' }}>Error: </strong> {errorMsg}
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Output / State */}
      <div>
        {status === 'idle' ? (
          <div className="glass-panel flex items-center justify-center text-muted" style={{ height: '100%', minHeight: 400, flexDirection: 'column', gap: '1rem' }}>
            <LayoutDashboard size={48} style={{ opacity: 0.2 }} />
            <p>Task results will appear here</p>
          </div>
        ) : status === 'running' ? (
          <div className="glass-panel flex items-center justify-center text-muted" style={{ height: '100%', minHeight: 400, flexDirection: 'column', gap: '1rem' }}>
            <Loader2 size={48} className="spinner" style={{ color: 'var(--primary)', borderTopColor: 'transparent' }} />
            <p>Matching agents and executing task on-chain...</p>
          </div>
        ) : result ? (
          <div className="glass-panel" style={{ padding: '2rem', height: '100%', overflowY: 'auto', maxHeight: '80vh' }}>
            <div className="flex items-center justify-between mb-6">
              <h2>Execution Result</h2>
              {getStatusBadge(result.final_status)}
            </div>
            
            <div className="mb-4">
              <span className="text-muted text-sm block mb-1">Chosen Executor</span>
              <div className="glass-card" style={{ padding: '0.75rem', fontSize: '0.9rem' }}>
                {result.chosen_executor || 'None'}
              </div>
            </div>

            <div className="mb-4">
              <span className="text-muted text-sm block mb-1">Attempts Needed</span>
              <div className="glass-card" style={{ padding: '0.75rem', fontSize: '0.9rem' }}>
                {(result.retry_count || 0) + 1}
              </div>
            </div>

            {/* Escrow Link */}
            {result.escrow_tx_hash && (
              <div className="mb-4">
                <span className="text-muted text-sm block mb-1">Escrow Lock Tx</span>
                <a href={`${EXPLORER_BASE}${result.escrow_tx_hash}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', wordBreak: 'break-all' }}>
                  {result.escrow_tx_hash}
                </a>
              </div>
            )}
            
            {/* Resolution Link */}
            {result.reclaim_tx_hash && (
              <div className="mb-4">
                <span className="text-muted text-sm block mb-1">Resolution Tx (Release/Refund)</span>
                <a href={`${EXPLORER_BASE}${result.reclaim_tx_hash}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', wordBreak: 'break-all' }}>
                  {result.reclaim_tx_hash}
                </a>
              </div>
            )}

            <div className="mb-4">
              <span className="text-muted text-sm block mb-1">Executor Output</span>
              <pre className="glass-card" style={{ padding: '1rem', overflowX: 'auto', fontSize: '0.85rem', color: '#a7f3d0' }}>
                {result.executor_output || 'No output produced'}
              </pre>
            </div>
            
            {result.audit_history && result.audit_history.length > 0 && (
              <div className="mb-4">
                <span className="text-muted text-sm block mb-1">Final Audit Critique</span>
                <div className="glass-card" style={{ padding: '1rem', fontSize: '0.9rem', borderLeft: result.audit_history[result.audit_history.length-1].passed ? '4px solid var(--success)' : '4px solid var(--danger)' }}>
                  {result.audit_history[result.audit_history.length-1].critique}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

// Need to import LayoutDashboard here for the empty state
import { LayoutDashboard } from 'lucide-react';
