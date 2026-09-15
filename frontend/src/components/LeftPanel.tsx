import React, { useState } from 'react';
import { 
  Sparkles, 
  Send, 
  ShieldAlert, 
  CheckCircle, 
  Tag, 
  Database, 
  Plus, 
  RefreshCw,
  Layers,
  ChevronDown,
  ChevronRight,
  ArrowUpRight,
  Play
} from 'lucide-react';
import { DemoScenario, UserRole, TicketItem, ROLE_DEFINITIONS } from '../types';

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 1,
    title: 'Cairo DC — Colocation & Power SLA',
    tag: 'RAG',
    prompt: "What are the power redundancy and uptime SLA specifications for Link Datacenter's Cairo facility?",
    targetRole: 'customer',
    description: 'Qdrant hybrid semantic vector search over enterprise SLAs.',
  },
  {
    id: 2,
    title: 'My Support Tickets',
    tag: 'TICKETS',
    prompt: "Show me all my open support tickets and their current status",
    targetRole: 'customer',
    description: 'Queries Supabase PostgreSQL with customer tenant isolation.',
  },
  {
    id: 3,
    title: 'BGP Route & Connectivity Status',
    tag: 'EXTERNAL',
    prompt: "What is the current BGP routing status and any connectivity issues for our dedicated link?",
    targetRole: 'support_agent',
    description: 'Tavily external search with resilient fallback mechanism.',
  },
  {
    id: 4,
    title: 'HITL Refund Approval Flow',
    tag: 'HITL',
    prompt: "Process a full refund of $450 for customer account C-4892 due to confirmed SLA breach in August",
    targetRole: 'senior_agent',
    description: 'Triggers LangGraph __interrupt__ gate requiring supervisor sign-off.',
  },
  {
    id: 5,
    title: 'Role-Based Access (Unauthorized Test)',
    tag: 'RBAC',
    prompt: "Create a new ticket for a network outage in rack B-12 Cairo DC — priority critical",
    targetRole: 'customer',
    description: 'Demonstrates RBAC enforcement: Customer role gets 403 / Access Denied.',
  },
  {
    id: 6,
    title: 'Create Ticket (Authorized Agent)',
    tag: 'TICKETS',
    prompt: "Create an urgent ticket for server overheating in rack C-7, priority critical, hardware category",
    targetRole: 'support_agent',
    description: 'Authorized agent executes ticket creation in PostgreSQL database.',
  },
  {
    id: 7,
    title: 'Colocation vs Managed Hosting',
    tag: 'RAG',
    prompt: "Explain the difference between colocation and managed hosting at Link Datacenter",
    targetRole: 'customer',
    description: 'Synthesizes enterprise data center documentation from vector store.',
  },
  {
    id: 8,
    title: 'Admin DB Diagnostic Summary',
    tag: 'ADMIN',
    prompt: "Show me a diagnostic summary of all tickets created in the last 24 hours across all customers",
    targetRole: 'admin',
    description: 'Administrative diagnostic query across all system tenants.',
  },
];

interface LeftPanelProps {
  currentRole: UserRole;
  onSelectScenario: (scenario: DemoScenario) => void;
  onSelectRole: (role: UserRole) => void;
  lastIntent?: string;
  lastConfidence?: number;
  lastAuthorized?: boolean;
  lastSources?: string[];
  executionTrace?: { step_name: string; status: string; details?: any }[];
  tickets: TicketItem[];
  isLoadingTickets: boolean;
  onRefreshTickets: () => void;
  onCreateTicket: (payload: { title: string; description: string; priority: string; category: string }) => Promise<void>;
  onUpdateTicketStatus: (ticketId: number, status: 'open' | 'in_progress' | 'resolved' | 'closed') => Promise<void>;
}

export const LeftPanel: React.FC<LeftPanelProps> = ({
  currentRole,
  onSelectScenario,
  onSelectRole,
  lastIntent,
  lastConfidence,
  lastAuthorized,
  lastSources = [],
  executionTrace = [],
  tickets,
  isLoadingTickets,
  onRefreshTickets,
  onCreateTicket,
  onUpdateTicketStatus,
}) => {
  const [activeTab, setActiveTab] = useState<'scenarios' | 'inspector' | 'tickets' | 'trace'>('scenarios');
  const [expandedScenarios, setExpandedScenarios] = useState<Record<number, boolean>>({});
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState('high');
  const [newCategory, setNewCategory] = useState('hardware');
  const [isSubmittingTicket, setIsSubmittingTicket] = useState(false);

  const toggleScenario = (id: number) => {
    setExpandedScenarios((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setIsSubmittingTicket(true);
    try {
      await onCreateTicket({
        title: newTitle,
        description: newDesc,
        priority: newPriority,
        category: newCategory,
      });
      setNewTitle('');
      setNewDesc('');
      setShowCreateModal(false);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingTicket(false);
    }
  };

  const getTagBadgeStyle = (tag: DemoScenario['tag']) => {
    switch (tag) {
      case 'HITL':
        return { bg: 'var(--status-warning-bg)', text: 'var(--status-warning)', border: 'var(--status-warning-border)' };
      case 'RBAC':
        return { bg: 'var(--status-danger-bg)', text: 'var(--status-danger)', border: 'var(--status-danger-border)' };
      case 'TICKETS':
        return { bg: '#f1f5f9', text: 'var(--text-secondary)', border: '#cbd5e1' };
      case 'EXTERNAL':
        return { bg: 'var(--status-info-bg)', text: 'var(--status-info)', border: 'var(--status-info-border)' };
      default:
        return { bg: '#f8fafc', text: 'var(--text-primary)', border: 'var(--border-light)' };
    }
  };

  return (
    <div
      style={{
        width: '360px',
        minWidth: '320px',
        maxWidth: '400px',
        height: '100%',
        background: '#ffffff',
        borderRight: '1px solid var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Tab Bar */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-light)',
          background: '#f8fafc',
          padding: '4px 8px',
          gap: '4px',
        }}
      >
        <button
          onClick={() => setActiveTab('scenarios')}
          style={{
            flex: 1,
            padding: '6px 8px',
            fontSize: '11.5px',
            fontWeight: activeTab === 'scenarios' ? 700 : 500,
            borderRadius: 'var(--radius-sm)',
            background: activeTab === 'scenarios' ? '#ffffff' : 'transparent',
            color: activeTab === 'scenarios' ? 'var(--action-primary)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'scenarios' ? 'var(--shadow-sm)' : 'none',
            border: activeTab === 'scenarios' ? '1px solid var(--border-light)' : '1px solid transparent',
          }}
        >
          Scenarios
        </button>

        <button
          onClick={() => setActiveTab('inspector')}
          style={{
            flex: 1,
            padding: '6px 8px',
            fontSize: '11.5px',
            fontWeight: activeTab === 'inspector' ? 700 : 500,
            borderRadius: 'var(--radius-sm)',
            background: activeTab === 'inspector' ? '#ffffff' : 'transparent',
            color: activeTab === 'inspector' ? 'var(--action-primary)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'inspector' ? 'var(--shadow-sm)' : 'none',
            border: activeTab === 'inspector' ? '1px solid var(--border-light)' : '1px solid transparent',
          }}
        >
          Inspector
        </button>

        <button
          onClick={() => setActiveTab('tickets')}
          style={{
            flex: 1,
            padding: '6px 8px',
            fontSize: '11.5px',
            fontWeight: activeTab === 'tickets' ? 700 : 500,
            borderRadius: 'var(--radius-sm)',
            background: activeTab === 'tickets' ? '#ffffff' : 'transparent',
            color: activeTab === 'tickets' ? 'var(--action-primary)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'tickets' ? 'var(--shadow-sm)' : 'none',
            border: activeTab === 'tickets' ? '1px solid var(--border-light)' : '1px solid transparent',
          }}
        >
          Tickets ({tickets.length})
        </button>

        <button
          onClick={() => setActiveTab('trace')}
          style={{
            flex: 1,
            padding: '6px 8px',
            fontSize: '11.5px',
            fontWeight: activeTab === 'trace' ? 700 : 500,
            borderRadius: 'var(--radius-sm)',
            background: activeTab === 'trace' ? '#ffffff' : 'transparent',
            color: activeTab === 'trace' ? 'var(--action-primary)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'trace' ? 'var(--shadow-sm)' : 'none',
            border: activeTab === 'trace' ? '1px solid var(--border-light)' : '1px solid transparent',
          }}
        >
          Trace
        </button>
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {/* TAB 1: SCENARIOS (Progressive Disclosure) */}
        {activeTab === 'scenarios' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                Enterprise Test Scenarios
              </span>
              <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                Click to expand details
              </span>
            </div>

            {DEMO_SCENARIOS.map((sc) => {
              const isExpanded = expandedScenarios[sc.id] || false;
              const badgeStyle = getTagBadgeStyle(sc.tag);
              const isRoleMatch = currentRole === sc.targetRole;

              return (
                <div
                  key={sc.id}
                  style={{
                    border: '1px solid var(--border-light)',
                    borderRadius: 'var(--radius-sm)',
                    background: '#ffffff',
                    boxShadow: 'var(--shadow-sm)',
                    overflow: 'hidden',
                    transition: 'var(--transition)',
                  }}
                >
                  {/* Compact Header Row (Always Visible) */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      background: isExpanded ? '#f8fafc' : '#ffffff',
                      gap: '8px',
                    }}
                  >
                    <button
                      onClick={() => toggleScenario(sc.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        flex: 1,
                        minWidth: 0,
                        textAlign: 'left',
                      }}
                    >
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 800,
                          padding: '1px 5px',
                          borderRadius: '3px',
                          background: badgeStyle.bg,
                          color: badgeStyle.text,
                          border: `1px solid ${badgeStyle.border}`,
                          textTransform: 'uppercase',
                        }}
                      >
                        {sc.tag}
                      </span>
                      <span
                        style={{
                          fontSize: '12px',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {sc.title}
                      </span>
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <button
                        onClick={() => onSelectScenario(sc)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          background: 'var(--action-primary)',
                          color: '#ffffff',
                          fontSize: '11px',
                          fontWeight: 700,
                        }}
                        title="Run this scenario"
                      >
                        <span>Run</span>
                        <Play size={10} fill="#ffffff" />
                      </button>

                      <button
                        onClick={() => toggleScenario(sc.id)}
                        style={{
                          padding: '4px',
                          color: 'var(--text-muted)',
                        }}
                        title={isExpanded ? 'Collapse' : 'Expand details'}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Detail View (Revealed on Demand) */}
                  {isExpanded && (
                    <div
                      style={{
                        padding: '8px 10px 10px',
                        borderTop: '1px solid var(--border-light)',
                        background: '#fafbfc',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                        fontSize: '11.5px',
                      }}
                    >
                      <div
                        style={{
                          background: '#ffffff',
                          padding: '6px 8px',
                          borderRadius: '4px',
                          border: '1px solid var(--border-light)',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.4,
                          fontStyle: 'italic',
                        }}
                      >
                        "{sc.prompt}"
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '2px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>{sc.description}</span>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Role:</span>
                          <button
                            onClick={() => onSelectRole(sc.targetRole)}
                            style={{
                              fontSize: '10px',
                              fontWeight: 700,
                              padding: '1px 5px',
                              borderRadius: '3px',
                              background: isRoleMatch ? 'var(--status-success-bg)' : '#f1f5f9',
                              color: isRoleMatch ? 'var(--status-success)' : 'var(--text-secondary)',
                              border: isRoleMatch ? '1px solid var(--status-success-border)' : '1px solid var(--border-light)',
                            }}
                          >
                            {ROLE_DEFINITIONS[sc.targetRole].title}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* TAB 2: INSPECTOR */}
        {activeTab === 'inspector' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
              Semantic Intent Inspector
            </span>

            <div style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: '10px', background: '#ffffff' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Classified Intent
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12.5px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                  {lastIntent || 'awaiting_query'}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Confidence: <strong>{lastConfidence ? `${Math.round(lastConfidence * 100)}%` : '—'}</strong>
                </span>
              </div>
            </div>

            <div style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: '10px', background: '#ffffff' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                RBAC Authorization
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: lastAuthorized === false ? 'var(--status-danger)' : 'var(--status-success)' }}>
                  {lastAuthorized === false ? 'Denied (403)' : 'Authorized'}
                </span>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                  Role: {ROLE_DEFINITIONS[currentRole].clearance}
                </span>
              </div>
            </div>

            <div style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: '10px', background: '#ffffff' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Knowledge Sources ({lastSources.length})
              </div>
              {lastSources.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {lastSources.map((src, i) => (
                    <div key={i} style={{ fontSize: '11px', color: 'var(--text-secondary)', background: '#f8fafc', padding: '4px 6px', borderRadius: '4px', border: '1px solid var(--border-light)' }}>
                      &bull; {src}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  No citations retrieved for active query.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: TICKETS */}
        {activeTab === 'tickets' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                Support Tickets
              </span>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button onClick={onRefreshTickets} style={{ padding: '4px', border: '1px solid var(--border-light)', borderRadius: '4px' }}>
                  <RefreshCw size={12} className={isLoadingTickets ? 'animate-spin' : ''} />
                </button>
                <button
                  onClick={() => setShowCreateModal(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    background: 'var(--action-primary)',
                    color: '#ffffff',
                    fontSize: '11px',
                    fontWeight: 700,
                  }}
                >
                  <Plus size={11} />
                  <span>New</span>
                </button>
              </div>
            </div>

            {showCreateModal && (
              <form onSubmit={handleCreateSubmit} style={{ background: '#f8fafc', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <input
                  placeholder="Ticket title..."
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  required
                  style={{ width: '100%', padding: '5px 8px', fontSize: '11.5px' }}
                />
                <textarea
                  placeholder="Description..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  rows={2}
                  style={{ width: '100%', padding: '5px 8px', fontSize: '11.5px' }}
                />
                <div style={{ display: 'flex', gap: '4px' }}>
                  <select value={newPriority} onChange={(e) => setNewPriority(e.target.value)} style={{ flex: 1, padding: '4px', fontSize: '11px' }}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                  <select value={newCategory} onChange={(e) => setNewCategory(e.target.value)} style={{ flex: 1, padding: '4px', fontSize: '11px' }}>
                    <option value="hardware">Hardware</option>
                    <option value="network">Network</option>
                    <option value="security">Security</option>
                  </select>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px', marginTop: '2px' }}>
                  <button type="button" onClick={() => setShowCreateModal(false)} style={{ padding: '3px 8px', fontSize: '11px' }}>Cancel</button>
                  <button type="submit" disabled={isSubmittingTicket} style={{ padding: '3px 10px', fontSize: '11px', fontWeight: 700, background: 'var(--action-primary)', color: '#ffffff', borderRadius: '4px' }}>
                    {isSubmittingTicket ? '...' : 'Create'}
                  </button>
                </div>
              </form>
            )}

            {tickets.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', fontSize: '11.5px', color: 'var(--text-muted)' }}>
                No active tickets found.
              </div>
            ) : (
              tickets.map((t) => (
                <div key={t.id} style={{ border: '1px solid var(--border-light)', borderRadius: '4px', padding: '8px', background: '#ffffff', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>#{t.id}</span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 4px', borderRadius: '3px', background: t.priority === 'critical' ? '#fee2e2' : '#f1f5f9', color: t.priority === 'critical' ? '#dc2626' : 'var(--text-secondary)' }}>
                      {t.priority}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{t.title}</div>
                  <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>Category: {t.category} &bull; Status: {t.status}</div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 4: TRACE */}
        {activeTab === 'trace' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
              Execution Trace
            </span>
            {executionTrace.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', fontSize: '11.5px', color: 'var(--text-muted)' }}>
                No node executions recorded yet.
              </div>
            ) : (
              executionTrace.map((st, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px', border: '1px solid var(--border-light)', borderRadius: '4px', background: '#ffffff', fontSize: '11.5px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{st.step_name}</span>
                  <span style={{ fontSize: '9.5px', fontWeight: 700, color: st.status === 'success' ? 'var(--status-success)' : '#d97706' }}>{st.status}</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};
