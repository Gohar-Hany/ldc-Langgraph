import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  X, 
  Play, 
  Ticket, 
  RefreshCw, 
  Plus,
  Search,
  Database,
  Zap,
  Globe,
  ShieldCheck,
  Check,
  ChevronRight,
  Sparkles
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
    id: 7,
    title: 'Colocation vs Managed Hosting',
    tag: 'RAG',
    prompt: "Explain the difference between colocation and managed hosting at Link Datacenter",
    targetRole: 'customer',
    description: 'Synthesizes enterprise data center documentation from vector store.',
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
    id: 3,
    title: 'BGP Route & Connectivity Status',
    tag: 'EXTERNAL',
    prompt: "What is the current BGP routing status and any connectivity issues for our dedicated link?",
    targetRole: 'support_agent',
    description: 'Tavily external search with resilient fallback mechanism.',
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
    id: 6,
    title: 'Create Ticket (Authorized Agent)',
    tag: 'TICKETS',
    prompt: "Create an urgent ticket for server overheating in rack C-7, priority critical, hardware category",
    targetRole: 'support_agent',
    description: 'Authorized agent executes ticket creation in PostgreSQL database.',
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
    id: 8,
    title: 'Admin DB Diagnostic Summary',
    tag: 'ADMIN',
    prompt: "Show me a diagnostic summary of all tickets created in the last 24 hours across all customers",
    targetRole: 'admin',
    description: 'Administrative diagnostic query across all system tenants.',
  },
];

interface ScenarioGroup {
  id: string;
  title: string;
  icon: any;
  tagFilter: string[];
}

const SCENARIO_GROUPS: ScenarioGroup[] = [
  { id: 'rag', title: 'RAG & SLA Knowledge Queries', icon: Database, tagFilter: ['RAG'] },
  { id: 'hitl', title: 'Human-in-the-Loop (HITL) Actions', icon: Zap, tagFilter: ['HITL'] },
  { id: 'network', title: 'Network Routing & External Search', icon: Globe, tagFilter: ['EXTERNAL'] },
  { id: 'tickets', title: 'Support Ticket Operations', icon: Ticket, tagFilter: ['TICKETS'] },
  { id: 'security', title: 'Security & RBAC Enforcement', icon: ShieldCheck, tagFilter: ['RBAC', 'ADMIN'] },
];

interface ScenariosDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentRole: UserRole;
  onSelectScenario: (scenario: DemoScenario) => void;
  onSelectRole: (role: UserRole) => void;
  tickets: TicketItem[];
  isLoadingTickets: boolean;
  onRefreshTickets: () => void;
  onCreateTicket: (payload: { title: string; description: string; priority: string; category: string }) => Promise<void>;
  defaultTab?: 'scenarios' | 'tickets';
  isMobile?: boolean;
}

export const ScenariosDrawer: React.FC<ScenariosDrawerProps> = ({
  isOpen,
  onClose,
  currentRole,
  onSelectScenario,
  onSelectRole,
  tickets,
  isLoadingTickets,
  onRefreshTickets,
  onCreateTicket,
  defaultTab = 'scenarios',
  isMobile = false,
}) => {
  const [activeTab, setActiveTab] = useState<'scenarios' | 'tickets'>(defaultTab);
  const [searchQuery, setSearchQuery] = useState('');
  const [showNewTicket, setShowNewTicket] = useState(false);
  const [ticketTitle, setTicketTitle] = useState('');
  const [ticketDesc, setTicketDesc] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Sync active tab
  useEffect(() => {
    if (defaultTab) {
      setActiveTab(defaultTab);
    }
  }, [defaultTab, isOpen]);

  // Focus search on open
  useEffect(() => {
    if (isOpen && activeTab === 'scenarios') {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 150);
    }
  }, [isOpen, activeTab]);

  // Support ESC key to dismiss panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const getTagStyle = (tag: DemoScenario['tag']) => {
    switch (tag) {
      case 'HITL':
        return { bg: '#fffbeb', text: '#b45309', border: '#fde68a' };
      case 'RBAC':
      case 'ADMIN':
        return { bg: '#fef2f2', text: '#b91c1c', border: '#fecaca' };
      case 'EXTERNAL':
        return { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' };
      case 'RAG':
        return { bg: '#faf5ff', text: '#6d28d9', border: '#ede9fe' };
      case 'TICKETS':
        return { bg: '#ecfdf5', text: '#047857', border: '#a7f3d0' };
      default:
        return { bg: '#f8fafc', text: '#475569', border: '#cbd5e1' };
    }
  };

  // Filtered scenarios
  const filteredScenarios = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return DEMO_SCENARIOS;

    return DEMO_SCENARIOS.filter((sc) => {
      const matchTitle = sc.title.toLowerCase().includes(query);
      const matchDesc = sc.description.toLowerCase().includes(query);
      const matchPrompt = sc.prompt.toLowerCase().includes(query);
      const matchTag = sc.tag.toLowerCase().includes(query);
      const matchRole = ROLE_DEFINITIONS[sc.targetRole].title.toLowerCase().includes(query);
      return matchTitle || matchDesc || matchPrompt || matchTag || matchRole;
    });
  }, [searchQuery]);

  // Grouped results
  const groupedScenarios = useMemo(() => {
    return SCENARIO_GROUPS.map((group) => {
      const items = filteredScenarios.filter((sc) => group.tagFilter.includes(sc.tag));
      return {
        ...group,
        items,
      };
    }).filter((group) => group.items.length > 0);
  }, [filteredScenarios]);

  const handleTicketSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketTitle.trim()) return;
    await onCreateTicket({
      title: ticketTitle,
      description: ticketDesc,
      priority: 'high',
      category: 'hardware',
    });
    setTicketTitle('');
    setTicketDesc('');
    setShowNewTicket(false);
  };

  if (!isOpen) return null;

  return (
    <aside
      aria-label="Scenarios and Tickets Reference Panel"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: isMobile ? '100vw' : '450px',
        maxWidth: isMobile ? '100vw' : '90vw',
        background: '#ffffff',
        boxShadow: '-6px 0 25px rgba(15, 23, 42, 0.08)',
        zIndex: 60,
        display: 'flex',
        flexDirection: 'column',
        borderLeft: isMobile ? 'none' : '1px solid #e2e8f0',
        animation: 'slideInRight 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* 1. Panel Header: Tabs + Close Button */}
      <div
        style={{
          padding: isMobile ? '10px 14px' : '12px 18px',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#ffffff',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setActiveTab('scenarios')}
            style={{
              fontSize: '12px',
              fontWeight: 700,
              padding: isMobile ? '6px 10px' : '5px 12px',
              borderRadius: '6px',
              background: activeTab === 'scenarios' ? '#0f172a' : 'transparent',
              color: activeTab === 'scenarios' ? '#ffffff' : '#64748b',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            Scenarios ({DEMO_SCENARIOS.length})
          </button>

          <button
            onClick={() => setActiveTab('tickets')}
            style={{
              fontSize: '12px',
              fontWeight: 700,
              padding: isMobile ? '6px 10px' : '5px 12px',
              borderRadius: '6px',
              background: activeTab === 'tickets' ? '#0f172a' : 'transparent',
              color: activeTab === 'tickets' ? '#ffffff' : '#64748b',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            Tickets ({tickets.length})
          </button>
        </div>

        <button
          onClick={onClose}
          title="Close Panel (Esc)"
          style={{
            padding: '6px',
            width: isMobile ? '34px' : 'auto',
            height: isMobile ? '34px' : 'auto',
            color: '#64748b',
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* 2. Command Palette Search Bar (Fixed at top when scenarios tab active) */}
      {activeTab === 'scenarios' && (
        <div
          style={{
            padding: '10px 18px',
            borderBottom: '1px solid #f1f5f9',
            background: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: '8px',
              padding: '6px 10px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          >
            <Search size={14} color="#94a3b8" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter scenarios (e.g. refund, SLA, BGP, ticket)..."
              style={{
                flex: 1,
                border: 'none',
                background: 'transparent',
                fontSize: '12px',
                color: '#0f172a',
                outline: 'none',
              }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                title="Clear search"
                style={{
                  border: 'none',
                  background: 'transparent',
                  color: '#94a3b8',
                  padding: '2px',
                  cursor: 'pointer',
                }}
              >
                <X size={12} />
              </button>
            )}
          </div>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', whiteSpace: 'nowrap' }}>
            {filteredScenarios.length} of {DEMO_SCENARIOS.length}
          </span>
        </div>
      )}

      {/* 3. Panel Body Scroll Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 18px', background: '#ffffff' }}>
        {activeTab === 'scenarios' ? (
          filteredScenarios.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: '#94a3b8' }}>
              <Search size={28} style={{ margin: '0 auto 8px auto', opacity: 0.5 }} />
              <p style={{ margin: 0, fontSize: '13px', fontWeight: 600, color: '#475569' }}>
                No matching scenarios found
              </p>
              <p style={{ margin: '4px 0 0 0', fontSize: '11.5px' }}>
                Try searching for "SLA", "refund", "ticket", or "BGP".
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {groupedScenarios.map((group) => {
                const GroupIcon = group.icon;
                return (
                  <div key={group.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {/* Section Header */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '2px 4px' }}>
                      <GroupIcon size={13} color="#059669" />
                      <span style={{ fontSize: '11px', fontWeight: 800, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                        {group.title}
                      </span>
                      <span style={{ fontSize: '10.5px', color: '#94a3b8', fontWeight: 600 }}>
                        ({group.items.length})
                      </span>
                    </div>

                    {/* Scenarios in Group: Rigid Column Layout & Full Row Click */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                      {group.items.map((sc) => {
                        const tagStyle = getTagStyle(sc.tag);
                        const isRoleMatch = currentRole === sc.targetRole;
                        const roleInfo = ROLE_DEFINITIONS[sc.targetRole];

                        return (
                          <div
                            key={sc.id}
                            onClick={() => {
                              onSelectScenario(sc);
                              onClose();
                            }}
                            title={`Click to run scenario: "${sc.title}"\nPrompt: "${sc.prompt}"`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              padding: '8px 10px',
                              borderRadius: '8px',
                              background: '#ffffff',
                              border: '1px solid #e2e8f0',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = '#f8fafc';
                              e.currentTarget.style.borderColor = '#059669';
                              e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.04)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = '#ffffff';
                              e.currentTarget.style.borderColor = '#e2e8f0';
                              e.currentTarget.style.boxShadow = 'none';
                            }}
                          >
                            {/* Column 1: Fixed-width Tag Badge */}
                            <div style={{ width: '72px', minWidth: '72px', display: 'flex', justifyContent: 'center' }}>
                              <span
                                style={{
                                  width: '100%',
                                  textAlign: 'center',
                                  fontSize: '9.5px',
                                  fontWeight: 800,
                                  padding: '2px 0',
                                  borderRadius: '4px',
                                  background: tagStyle.bg,
                                  color: tagStyle.text,
                                  border: `1px solid ${tagStyle.border}`,
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.02em',
                                }}
                              >
                                {sc.tag}
                              </span>
                            </div>

                            {/* Column 2: Flexible Title & Prompt Subtitle with Tooltip */}
                            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '1px' }}>
                              <span
                                style={{
                                  fontSize: '12px',
                                  fontWeight: 600,
                                  color: '#0f172a',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                                title={sc.title}
                              >
                                {sc.title}
                              </span>
                              <span
                                style={{
                                  fontSize: '10.5px',
                                  color: '#64748b',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                                title={sc.description}
                              >
                                {sc.description}
                              </span>
                            </div>

                            {/* Column 3: Fixed-width Clearance Level Badge */}
                            <div
                              style={{ width: '42px', minWidth: '42px', display: 'flex', justifyContent: 'center' }}
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectRole(sc.targetRole);
                              }}
                              title={`Target clearance: ${roleInfo.title} (${roleInfo.clearance}). Click to switch role only.`}
                            >
                              <span
                                style={{
                                  width: '100%',
                                  textAlign: 'center',
                                  fontSize: '9.5px',
                                  fontWeight: 700,
                                  padding: '2px 0',
                                  borderRadius: '4px',
                                  background: isRoleMatch ? '#ecfdf5' : '#f1f5f9',
                                  color: isRoleMatch ? '#047857' : '#64748b',
                                  border: isRoleMatch ? '1px solid #a7f3d0' : '1px solid #e2e8f0',
                                }}
                              >
                                {roleInfo.clearance}
                              </span>
                            </div>

                            {/* Column 4: Fixed-width Run Action Button */}
                            <div style={{ width: '58px', minWidth: '58px', display: 'flex', justifyContent: 'flex-end' }}>
                              <button
                                style={{
                                  width: '100%',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  gap: '3px',
                                  padding: '4px 0',
                                  borderRadius: '5px',
                                  background: '#064e3b',
                                  color: '#ffffff',
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  border: 'none',
                                  cursor: 'pointer',
                                }}
                              >
                                <span>Run</span>
                                <Play size={8} fill="#ffffff" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )
        ) : (
          /* Tickets Management Section */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '4px', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Ticket size={14} color="#059669" />
                <span style={{ fontSize: '12px', fontWeight: 800, color: '#0f172a' }}>POSTGRESQL TICKETS</span>
              </div>

              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  onClick={onRefreshTickets}
                  disabled={isLoadingTickets}
                  title="Refresh tickets from DB"
                  style={{
                    padding: '4px 6px',
                    borderRadius: '5px',
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    color: '#64748b',
                    cursor: 'pointer',
                  }}
                >
                  <RefreshCw size={12} className={isLoadingTickets ? 'spin' : ''} />
                </button>

                <button
                  onClick={() => setShowNewTicket(true)}
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '4px 8px',
                    background: '#064e3b',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <Plus size={11} />
                  <span>New Ticket</span>
                </button>
              </div>
            </div>

            {showNewTicket && (
              <form
                onSubmit={handleTicketSubmit}
                style={{
                  padding: '12px',
                  background: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  borderRadius: '8px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#0f172a' }}>Create Support Ticket</span>
                <input
                  placeholder="Ticket Title (e.g. BGP latency issue)..."
                  value={ticketTitle}
                  onChange={(e) => setTicketTitle(e.target.value)}
                  required
                  style={{ padding: '6px 8px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
                />
                <textarea
                  placeholder="Detailed description and affected rack/IP..."
                  value={ticketDesc}
                  onChange={(e) => setTicketDesc(e.target.value)}
                  rows={2}
                  style={{ padding: '6px 8px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '4px', resize: 'none' }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                  <button
                    type="button"
                    onClick={() => setShowNewTicket(false)}
                    style={{ fontSize: '11px', padding: '4px 8px', background: '#e2e8f0', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    style={{ fontSize: '11px', fontWeight: 700, background: '#064e3b', color: '#ffffff', padding: '4px 10px', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    Create
                  </button>
                </div>
              </form>
            )}

            {tickets.length === 0 ? (
              <div style={{ padding: '24px 0', textAlign: 'center', color: '#94a3b8', fontSize: '12px' }}>
                No support tickets found in database.
              </div>
            ) : (
              tickets.map((t) => (
                <div
                  key={t.id}
                  style={{
                    border: '1px solid #e2e8f0',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    background: '#ffffff',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '3px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '10.5px', fontWeight: 700, color: '#64748b' }}>#{t.id}</span>
                    <span
                      style={{
                        textTransform: 'uppercase',
                        fontWeight: 700,
                        fontSize: '9.5px',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        background: t.priority === 'critical' ? '#fee2e2' : '#f1f5f9',
                        color: t.priority === 'critical' ? '#b91c1c' : '#475569',
                      }}
                    >
                      {t.priority}
                    </span>
                  </div>
                  <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '12px' }}>{t.title}</div>
                  {t.description && (
                    <div style={{ color: '#64748b', fontSize: '11px', lineHeight: 1.3 }}>{t.description}</div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </aside>
  );
};
