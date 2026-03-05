import React, { useState, useEffect } from 'react';
import { Search, MapPin, Send, Zap, Loader2, Play, Building2, CheckCircle2, FileText, Mail, User, Linkedin, History, Trash2, ExternalLink, Phone, PhoneCall } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [query, setQuery] = useState('Top real estate agencies');
  const [city, setCity] = useState('Miami');
  const [isHunting, setIsHunting] = useState(false);
  const [leads, setLeads] = useState([]);
  const [logs, setLogs] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [intelLead, setIntelLead] = useState(null); // Intelligence state
  const [editedDraft, setEditedDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [activeTab, setActiveTab] = useState('radar'); // 'radar' or 'command'
  const LEADS_PER_PAGE = 6;

  // Check if any lead is currently generating an AI draft OR initiating a call
  const isGenerating = leads.some(
    l => l.status?.toLowerCase().includes('generating') ||
      l.status?.toLowerCase().includes('calling')
  );

  // Poll for leads & logs while hunting OR while any lead is being AI-drafted
  useEffect(() => {
    let interval;
    if (isHunting || leads.length > 0 || isGenerating) {
      interval = setInterval(async () => {
        try {
          const resLeads = await fetch(`${API_BASE}/api/leads`);
          if (resLeads.ok) {
            const data = await resLeads.json();
            setLeads(data.leads);
            if (isHunting && data.leads.length >= 30) setIsHunting(false);
          }

          const resStatus = await fetch(`${API_BASE}/api/status`);
          if (resStatus.ok) {
            const data = await resStatus.json();
            if (isHunting && !data.is_hunting) setIsHunting(false);
          }

          const resLogs = await fetch(`${API_BASE}/api/logs`);
          if (resLogs.ok) {
            const data = await resLogs.json();
            setLogs(data.logs);
          }
        } catch (e) {
          console.error("Polling failed");
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isHunting, leads.length, isGenerating]);

  const handleTarget = async (e) => {
    e.preventDefault();
    setIsHunting(true);
    setLeads([]);
    setCurrentPage(1);
    try {
      await fetch(`${API_BASE}/api/target`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, city })
      });
    } catch (e) {
      console.error(e);
      setIsHunting(false);
    }
  };

  const handleGenerateDraft = async (leadId) => {
    try {
      setLeads(prev => prev.map(l => l.id === leadId ? { ...l, status: 'generating' } : l));
      await fetch(`${API_BASE}/api/generate-draft/${leadId}`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const openModal = (lead) => {
    if (!lead.drafted_email) return;
    setSelectedLead(lead);
    setEditedDraft(lead.drafted_email);
  };

  const handleSendEmail = async () => {
    if (!selectedLead) return;
    setIsSending(true);
    try {
      const resp = await fetch(`${API_BASE}/api/send/${selectedLead.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email_body: editedDraft })
      });
      if (resp.ok) {
        setLeads(prev => prev.map(l =>
          l.id === selectedLead.id ? { ...l, status: 'SENT 🚀', drafted_email: editedDraft } : l
        ));
        setSelectedLead(null);
      } else {
        const err = await resp.json();
        alert(`Send failed: ${err.detail}`);
      }
    } catch (e) {
      console.error(e);
      alert('Network error — could not reach backend.');
    } finally {
      setIsSending(false);
    }
  };

  const handleVoiceCall = async (leadId) => {
    try {
      setLeads(prev => prev.map(l =>
        l.id === leadId ? { ...l, status: 'Calling...' } : l
      ));
      const resp = await fetch(`${API_BASE}/api/voice-call/${leadId}`, { method: 'POST' });
      if (!resp.ok) {
        const err = await resp.json();
        alert(`Voice call failed: ${err.detail}`);
        // revert status
        setLeads(prev => prev.map(l =>
          l.id === leadId ? { ...l, status: l.phone ? 'Identified' : l.status } : l
        ));
      }
    } catch (e) {
      console.error('Voice call error:', e);
    }
  };

  const getStatusClass = (status) => {
    if (!status) return '';
    if (status.includes('Verified')) return 'status-found';
    if (status.toLowerCase().includes('generating')) return 'status-generating';
    if (status.includes('Drafted')) return 'status-drafted';
    if (status.includes('SENT')) return 'status-sent';
    if (status.includes('Call Initiated')) return 'status-called';
    if (status.toLowerCase().includes('calling')) return 'status-generating';
    if (status.includes('Identified')) return 'status-identified';
    return '';
  };

  const indexOfLastLead = currentPage * LEADS_PER_PAGE;
  const indexOfFirstLead = indexOfLastLead - LEADS_PER_PAGE;
  const currentLeads = leads.slice(indexOfFirstLead, indexOfLastLead);
  const totalPages = Math.ceil(leads.length / LEADS_PER_PAGE);

  const stats = {
    hunted: leads.length,
    sent: logs.filter(l => l.status === 'SUCCESS').length,
    failed: logs.filter(l => l.status === 'FAILED').length,
    efficiency: leads.length > 0 ? Math.round((logs.length / leads.length) * 100) : 0
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1 className="header-title">Hyper-Nova Engine</h1>
        <p className="header-subtitle">AI Lead Acquisition & Engagement</p>
      </header>

      {/* Tabs Navigation */}
      <div className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'radar' ? 'active' : ''}`}
          onClick={() => setActiveTab('radar')}
        >
          <Zap size={18} /> AI Radar
        </button>
        <button
          className={`tab-btn ${activeTab === 'command' ? 'active' : ''}`}
          onClick={() => setActiveTab('command')}
        >
          <FileText size={18} /> Command Center
        </button>
      </div>

      {activeTab === 'radar' ? (
        <div className="glass-panel">
          <form onSubmit={handleTarget} className="search-form">
            <div style={{ position: 'relative', flex: 1.5 }}>
              <Search style={{ position: 'absolute', top: '1rem', left: '1rem', color: '#94a3b8' }} size={20} />
              <input
                className="input-field"
                style={{ paddingLeft: '3rem', width: '100%' }}
                value={query} onChange={(e) => setQuery(e.target.value)}
                placeholder="Target Persona (e.g. Real estate agencies)"
                required
              />
            </div>
            <div style={{ position: 'relative', flex: 1 }}>
              <MapPin style={{ position: 'absolute', top: '1rem', left: '1rem', color: '#94a3b8' }} size={20} />
              <input
                className="input-field"
                style={{ paddingLeft: '3rem', width: '100%' }}
                value={city} onChange={(e) => setCity(e.target.value)}
                placeholder="Location (e.g. Miami)"
                required
              />
            </div>
            <button type="submit" className="btn" disabled={isHunting}>
              {isHunting ? <Loader2 className="spin" /> : <Zap />}
              {isHunting ? 'Hunting...' : 'Deploy AI Radar'}
            </button>
          </form>

          <div className="leads-grid" style={{ minHeight: '400px' }}>
            {currentLeads.map(lead => (
              <div key={lead.id} className="lead-card">
                <div className="lead-header">
                  <div>
                    <h3 className="lead-title" title={lead.company_name}>{lead.company_name}</h3>
                    <a href={lead.website} target="_blank" rel="noreferrer" className="lead-link">{lead.website.replace('https://', '')}</a>
                  </div>
                  <span className={`lead-status ${getStatusClass(lead.status)}`}>{lead.status}</span>
                </div>

                <div className="lead-meta" onClick={() => setIntelLead(lead)} style={{ cursor: 'pointer' }}>
                  <Mail size={14} color="#6366f1" />
                  <span>{lead.email || 'Email missing...'}</span>
                  {lead.intel?.founder && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '12px', color: '#818cf8' }}>
                      <User size={14} />
                      <span style={{ fontSize: '0.75rem', fontWeight: '600' }}>{lead.intel.founder}</span>
                    </div>
                  )}
                </div>

                <div className="lead-meta" style={{ marginTop: '4px', opacity: 0.8, fontSize: '0.75rem' }}>
                  <MapPin size={12} />
                  <span className="truncate">{lead.intel?.address || 'Address not found'}</span>
                </div>

                {lead.phone && (
                  <div className="lead-meta" style={{ marginTop: '2px', opacity: 0.8, fontSize: '0.75rem' }}>
                    <Phone size={12} color="#10b981" />
                    <span style={{ color: '#10b981', fontWeight: 600 }}>{lead.phone}</span>
                  </div>
                )}

                {lead.drafted_email ? (
                  <div className="lead-draft-box" style={{ cursor: 'pointer' }} onClick={() => openModal(lead)}>
                    <strong>AI Draft snippet:</strong><br />
                    <span style={{ color: '#94a3b8' }}>{lead.drafted_email.substring(0, 100)}...</span>
                  </div>
                ) : (
                  <div className="lead-draft-box" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontStyle: 'italic', color: '#64748b' }}>
                    No drafted email yet
                  </div>
                )}

                <div className="lead-actions">
                  {!lead.drafted_email && !lead.status?.toLowerCase().includes('generating') && (
                    <button className="btn btn-secondary" style={{ flex: 1, padding: '0.75rem', fontSize: '0.875rem' }} onClick={() => handleGenerateDraft(lead.id)}>
                      <FileText size={16} /> Draft Pitch
                    </button>
                  )}
                  {lead.status?.toLowerCase().includes('generating') && (
                    <button className="btn btn-secondary" style={{ flex: 1, padding: '0.75rem', fontSize: '0.875rem' }} disabled>
                      <Loader2 className="spin" size={16} /> AI thinking...
                    </button>
                  )}
                  {lead.drafted_email && !lead.status?.includes('SENT') && (
                    <button className="btn btn-secondary" style={{ flex: 1, padding: '0.75rem', fontSize: '0.875rem', borderColor: '#4f46e5' }} onClick={() => openModal(lead)}>
                      <CheckCircle2 size={16} color="#6366f1" /> Review & Send
                    </button>
                  )}
                  {lead.phone && !lead.status?.includes('Call') && !lead.status?.toLowerCase().includes('calling') && (
                    <button
                      className="btn btn-voice"
                      style={{ padding: '0.75rem', fontSize: '0.875rem' }}
                      onClick={() => handleVoiceCall(lead.id)}
                      title={`Call ${lead.phone}`}
                    >
                      <PhoneCall size={16} />
                    </button>
                  )}
                  {lead.status?.toLowerCase().includes('calling') && (
                    <button className="btn btn-voice" style={{ padding: '0.75rem', fontSize: '0.875rem' }} disabled>
                      <Loader2 className="spin" size={16} />
                    </button>
                  )}
                  {lead.status?.includes('Call Initiated') && (
                    <button className="btn btn-voice" style={{ padding: '0.75rem', fontSize: '0.875rem', opacity: 0.7 }} disabled>
                      <Phone size={16} /> Called
                    </button>
                  )}
                  {lead.status?.includes('SENT') && (
                    <button className="btn btn-success" style={{ flex: 1, padding: '0.75rem', fontSize: '0.875rem' }} disabled>
                      Sent 🚀
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {leads.length > 0 && (
            <div className="pagination">
              <button
                className="btn btn-secondary"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(prev => prev - 1)}
              >
                Previous
              </button>
              <span style={{ color: '#94a3b8' }}>Page {currentPage} of {Math.max(1, totalPages)}</span>
              <button
                className="btn btn-secondary"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage(prev => prev + 1)}
              >
                Next
              </button>
            </div>
          )}

        </div>
      ) : (
        <div className="command-center">
          {/* Stats Cards */}
          <div className="stats-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
            <div className="stat-card">
              <span className="stat-label">Successful Deliveries</span>
              <span className="stat-value" style={{ color: '#10b981' }}>{stats.sent}</span>
              <div className="stat-trend">SMTP handshakes verified</div>
            </div>
            <div className="stat-card">
              <span className="stat-label">System Blocked / Bounced</span>
              <span className="stat-value" style={{ color: '#ef4444' }}>{stats.failed}</span>
              <div className="stat-trend">Detected by mail-flow rules</div>
            </div>
          </div>

          <div className="glass-panel" style={{ marginTop: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--surface-border)', paddingBottom: '1rem' }}>
              <FileText size={24} color="var(--primary-color)" />
              <h2 style={{ fontSize: '1.5rem', fontWeight: '700' }}>Outreach History & Real-Time Logs</h2>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="logs-table">
                <thead>
                  <tr>
                    <th>Date / Time</th>
                    <th>Recipient Agency</th>
                    <th>Delivery Status</th>
                    <th>Server Response</th>
                    <th>Campaign Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr><td colSpan="5" style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>No outreach activity recorded yet. Deploy Radar to start.</td></tr>
                  ) : (
                    logs.slice().reverse().map(log => (
                      <tr key={log.id}>
                        <td style={{ color: 'var(--text-muted)' }}>{log.date}</td>
                        <td>
                          <div style={{ fontWeight: '600' }}>{log.company_name}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{log.email}</div>
                        </td>
                        <td>
                          <span className={`log-badge ${log.status === 'SUCCESS' ? 'badge-success' : 'badge-error'}`}>
                            {log.status}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{log.response}</td>
                        <td style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>{log.notes}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )
      }

      {
        selectedLead && (
          <div className="modal-overlay" onClick={() => setSelectedLead(null)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <button className="modal-close" onClick={() => setSelectedLead(null)}>✕</button>
              <h2 style={{ marginBottom: '0.5rem', fontSize: '1.5rem' }}>Review Protocol</h2>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                Final review for <strong style={{ color: 'white' }}>{selectedLead.company_name}</strong>
              </p>

              <textarea
                className="email-textarea"
                value={editedDraft}
                onChange={e => setEditedDraft(e.target.value)}
              />

              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setSelectedLead(null)}>Cancel</button>
                {selectedLead?.phone && (
                  <button
                    className="btn btn-voice"
                    onClick={() => { handleVoiceCall(selectedLead.id); setSelectedLead(null); }}
                    title={`Call ${selectedLead.phone}`}
                  >
                    <PhoneCall size={18} /> Voice Call
                  </button>
                )}
                <button className="btn" onClick={handleSendEmail} disabled={isSending}>
                  {isSending ? <Loader2 className="spin" /> : <Send size={18} />}
                  Deploy Email
                </button>
              </div>
            </div>
          </div>
        )
      }
      {
        intelLead && (
          <div className="modal-overlay" onClick={() => setIntelLead(null)}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '450px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                <div>
                  <h2 style={{ margin: 0 }}>Business Intelligence</h2>
                  <p style={{ color: '#94a3b8', margin: '4px 0' }}>Deep-scan for {intelLead.company_name}</p>
                </div>
                <button onClick={() => setIntelLead(null)} className="btn-close">×</button>
              </div>

              <div className="intel-row">
                <div className="intel-label"><User size={16} /> Decision Maker</div>
                <div className="intel-value">{intelLead.intel?.founder || "Not identified"}</div>
              </div>

              <div className="intel-row">
                <div className="intel-label"><MapPin size={16} /> Office Address</div>
                <div className="intel-value" style={{ lineHeight: '1.4' }}>{intelLead.intel?.address || "Scanned general area"}</div>
              </div>

              <div className="intel-row">
                <div className="intel-label"><Linkedin size={16} /> LinkedIn Profile</div>
                <div className="intel-value">
                  {intelLead.intel?.linkedin ? (
                    <a href={intelLead.intel.linkedin} target="_blank" rel="noreferrer" style={{ color: '#6366f1' }}>
                      Connect <ExternalLink size={12} />
                    </a>
                  ) : "No direct link"}
                </div>
              </div>

              <button className="btn" style={{ width: '100%', marginTop: '1rem' }} onClick={() => setIntelLead(null)}>
                Close Insights
              </button>
            </div>
          </div>
        )
      }
    </div >
  );
}

export default App;
