import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, CheckCircle, XCircle, AlertOctagon, Loader2 } from 'lucide-react';

const API_BASE = 'http://localhost:8000';
const EXPLORER_BASE = 'https://amoy.polygonscan.com/tx/';

export default function Escalations() {
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resolvingId, setResolvingId] = useState(null);

  const fetchEscalations = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/escalations`);
      // sort unresolved first
      const sorted = (res.data.escalations || []).sort((a, b) => (a.resolved === b.resolved ? 0 : a.resolved ? 1 : -1));
      setEscalations(sorted);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
  }, []);

  const handleResolve = async (taskId, decision) => {
    if (!window.confirm(`Are you sure you want to ${decision.toUpperCase()} this task?`)) return;
    setResolvingId(taskId);
    try {
      await axios.post(`${API_BASE}/escalations/${taskId}/resolve`, {
        decision: decision,
        reviewer_note: `Manual resolution by admin: ${decision}`
      });
      fetchEscalations();
    } catch (err) {
      console.error(err);
      alert('Error resolving escalation: ' + (err.response?.data?.detail || err.message));
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2>Human Escalation Queue</h2>
          <p className="text-muted text-sm mt-1">Tasks that failed max retries require manual review to decide escrow resolution.</p>
        </div>
        <button onClick={fetchEscalations} className="btn btn-outline flex items-center gap-2">
          <RefreshCw size={16} className={loading ? "spinner" : ""} /> Refresh
        </button>
      </div>

      {loading && escalations.length === 0 ? (
        <div className="flex items-center justify-center text-muted" style={{ height: 200 }}>
          <Loader2 size={32} className="spinner" />
        </div>
      ) : escalations.length === 0 ? (
        <div className="glass-panel flex flex-col items-center justify-center text-muted" style={{ height: 300, textAlign: 'center' }}>
          <AlertOctagon size={48} className="mb-4" style={{ opacity: 0.3 }} />
          <h3>No Escalations</h3>
          <p>The queue is empty. All tasks have been resolved automatically.</p>
        </div>
      ) : (
        <div className="grid gap-6">
          {escalations.map((esc) => (
            <div key={esc.task_id} className="glass-panel" style={{ padding: '1.5rem' }}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="mb-1">Task: {esc.task_id.split('-')[0]}...</h3>
                  <div className="text-muted text-sm">{esc.description}</div>
                </div>
                {esc.resolved ? (
                  <span className={`badge ${esc.resolution === 'approve' ? 'badge-green' : 'badge-red'}`}>
                    RESOLVED: {esc.resolution.toUpperCase()}
                  </span>
                ) : (
                  <span className="badge badge-yellow">PENDING REVIEW</span>
                )}
              </div>

              <div className="glass-card mb-4" style={{ padding: '1rem', background: 'rgba(245,158,11,0.1)', borderLeft: '4px solid #f59e0b' }}>
                <strong style={{ color: '#f59e0b' }}>Escalation Reason:</strong> {esc.escalation_reason || 'Max retries exceeded'}
              </div>

              {esc.audit_history && esc.audit_history.length > 0 && (
                <div className="mb-4">
                  <span className="text-muted text-sm block mb-1">Audit History (Last Attempt)</span>
                  <div className="glass-card" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
                    {esc.audit_history[esc.audit_history.length - 1].critique}
                  </div>
                </div>
              )}

              {esc.resolved && esc.resolution_tx_hash && (
                <div className="mt-4 mb-2">
                  <span className="text-muted text-sm block mb-1">Resolution Tx</span>
                  <a href={`${EXPLORER_BASE}${esc.resolution_tx_hash}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', wordBreak: 'break-all', fontSize: '0.85rem' }}>
                    {esc.resolution_tx_hash}
                  </a>
                </div>
              )}

              {!esc.resolved && (
                <div className="flex items-center gap-4 mt-6">
                  <button 
                    onClick={() => handleResolve(esc.task_id, 'approve')}
                    className="btn btn-success flex items-center gap-2"
                    disabled={resolvingId === esc.task_id}
                  >
                    {resolvingId === esc.task_id ? <Loader2 size={16} className="spinner" /> : <CheckCircle size={16} />}
                    Approve (Release Escrow)
                  </button>
                  <button 
                    onClick={() => handleResolve(esc.task_id, 'reject')}
                    className="btn btn-danger flex items-center gap-2"
                    disabled={resolvingId === esc.task_id}
                  >
                    {resolvingId === esc.task_id ? <Loader2 size={16} className="spinner" /> : <XCircle size={16} />}
                    Reject (Refund Client)
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
