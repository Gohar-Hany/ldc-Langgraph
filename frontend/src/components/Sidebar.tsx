import React, { useRef, useEffect } from 'react';
import { 
  MessageSquare, 
  PlayCircle, 
  Ticket, 
  ShieldCheck, 
  Search, 
  PanelLeftClose,
  PanelLeftOpen,
  Server,
  Activity,
  Sparkles,
  Cloud,
  X
} from 'lucide-react';

export interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  activeNav: string;
  onSelectNav: (navId: string) => void;
  scenariosCount?: number;
  openTicketsCount?: number;
  systemHealthText?: string;
  isSystemHealthy?: boolean;
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
  isMobile?: boolean;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  activeNav = 'chat',
  onSelectNav,
  scenariosCount = 8,
  openTicketsCount = 2,
  systemHealthText = 'System Operational',
  isSystemHealthy = true,
  searchQuery = '',
  onSearchChange,
  isMobile = false,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const searchInputRef = useRef<HTMLInputElement>(null);

  // When on mobile, drawer displays fully expanded
  const effectiveCollapsed = isMobile ? false : isCollapsed;

  // Keyboard shortcut listener for ⌘K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (!isMobile && isCollapsed) {
          onToggleCollapse();
        }
        setTimeout(() => {
          searchInputRef.current?.focus();
        }, 100);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCollapsed, onToggleCollapse, isMobile]);

  // Clean, 100% relevant navigation items for Link Datacenter
  const navItems = [
    {
      id: 'chat',
      label: 'Live Support Console',
      icon: MessageSquare,
      badge: 'LIVE',
      description: 'Autonomous chat & LangGraph execution',
    },
    {
      id: 'scenarios',
      label: 'Scenarios & Demos',
      icon: PlayCircle,
      badge: `${scenariosCount}`,
      description: 'RAG, HITL & RBAC benchmark runs',
    },
    {
      id: 'tickets',
      label: 'Support Tickets & SLA',
      icon: Ticket,
      badge: openTicketsCount > 0 ? `${openTicketsCount}` : null,
      description: 'Customer ticket management & dispatch',
    },
    {
      id: 'system',
      label: 'Infrastructure & RBAC',
      icon: ShieldCheck,
      badge: null,
      description: 'Cloud readiness & clearance policies',
    },
  ];

  return (
    <aside
      style={
        isMobile
          ? {
              position: 'fixed',
              top: 0,
              left: 0,
              bottom: 0,
              width: '280px',
              maxWidth: '85vw',
              height: '100vh',
              background: '#ffffff',
              boxShadow: isMobileOpen ? '4px 0 25px rgba(15, 23, 42, 0.15)' : 'none',
              transform: isMobileOpen ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
              zIndex: 100,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              userSelect: 'none',
            }
          : {
              width: isCollapsed ? '68px' : '260px',
              minWidth: isCollapsed ? '68px' : '260px',
              height: '100vh',
              background: '#ffffff',
              borderRight: '1px solid #e2e8f0',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
              position: 'relative',
              zIndex: 40,
              userSelect: 'none',
            }
      }
    >
      {/* Top Half: Header, Search, Navigation Items */}
      <div style={{ display: 'flex', flexDirection: 'column', padding: effectiveCollapsed ? '16px 8px' : '16px 14px', gap: '14px' }}>
        {/* Brand Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: effectiveCollapsed ? 'center' : 'space-between',
            gap: '8px',
            paddingBottom: '4px',
          }}
        >
          <div
            onClick={() => {
              onSelectNav('chat');
              if (isMobile && onCloseMobile) onCloseMobile();
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              cursor: 'pointer',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
              }}
            >
              <img
                src="/ldc_logo.webp"
                alt="LDC Logo"
                style={{ width: '24px', height: '24px', objectFit: 'contain' }}
              />
            </div>

            {!effectiveCollapsed && (
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
                <span style={{ fontSize: '13.5px', fontWeight: 800, color: '#0f172a', letterSpacing: '-0.01em' }}>
                  Link Datacenter
                </span>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#059669' }}>
                  Enterprise AI Support
                </span>
              </div>
            )}
          </div>

          {isMobile ? (
            <button
              onClick={onCloseMobile}
              title="Close Menu"
              style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                color: '#64748b',
                padding: '6px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <X size={18} />
            </button>
          ) : (
            !isCollapsed && (
              <button
                onClick={onToggleCollapse}
                title="Collapse sidebar"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  padding: '4px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <PanelLeftClose size={16} />
              </button>
            )
          )}
        </div>

        {/* Search Bar with ⌘K Badge */}
        {!effectiveCollapsed ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '6px 10px',
            }}
          >
            <Search size={14} color="#94a3b8" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange?.(e.target.value)}
              placeholder="Search cloud tools..."
              style={{
                flex: 1,
                border: 'none',
                background: 'transparent',
                fontSize: '12px',
                color: '#0f172a',
                outline: 'none',
              }}
            />
            <kbd
              style={{
                fontSize: '10px',
                fontWeight: 600,
                color: '#64748b',
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                borderRadius: '4px',
                padding: '1px 5px',
                lineHeight: '14px',
              }}
            >
              ⌘K
            </kbd>
          </div>
        ) : (
          <button
            onClick={onToggleCollapse}
            title="Search (⌘K)"
            style={{
              width: '100%',
              height: '34px',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#64748b',
              cursor: 'pointer',
            }}
          >
            <Search size={15} />
          </button>
        )}

        {/* Navigation Menu */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeNav === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectNav(item.id);
                  if (isMobile && onCloseMobile) onCloseMobile();
                }}
                title={effectiveCollapsed ? `${item.label} — ${item.description}` : undefined}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: effectiveCollapsed ? 'center' : 'space-between',
                  width: '100%',
                  padding: effectiveCollapsed ? '10px 0' : '9px 12px',
                  borderRadius: '9px',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  background: isActive ? '#064e3b' : 'transparent',
                  color: isActive ? '#ffffff' : '#334155',
                  boxShadow: isActive ? '0 2px 8px rgba(6, 78, 59, 0.2)' : 'none',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = '#f8fafc';
                    e.currentTarget.style.color = '#0f172a';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = '#334155';
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Icon
                    size={17}
                    color={isActive ? '#ffffff' : '#64748b'}
                    style={{ flexShrink: 0 }}
                  />
                  {!effectiveCollapsed && (
                    <span style={{ fontSize: '12.5px', fontWeight: isActive ? 700 : 500 }}>
                      {item.label}
                    </span>
                  )}
                </div>

                {!effectiveCollapsed && item.badge && (
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: '9999px',
                      background: isActive ? 'rgba(255, 255, 255, 0.25)' : '#e2e8f0',
                      color: isActive ? '#ffffff' : '#475569',
                      letterSpacing: '0.02em',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Section: LDC Cloud Status */}
      <div style={{ padding: effectiveCollapsed ? '12px 6px' : '14px 14px', borderTop: '1px solid #f1f5f9' }}>
        {!effectiveCollapsed ? (
          <div
            onClick={() => {
              onSelectNav('system');
              if (isMobile && onCloseMobile) onCloseMobile();
            }}
            style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '10px',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              cursor: 'pointer',
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#f0fdf4')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#f8fafc')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Server size={13} color="#059669" />
              <span style={{ fontSize: '11.5px', fontWeight: 800, color: '#0f172a' }}>
                LDC Cloud Node
              </span>
            </div>
            <span style={{ fontSize: '10.5px', color: '#64748b' }}>
              LangGraph Orchestrator v2.5
            </span>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: isSystemHealthy ? '#10b981' : '#f59e0b',
                  boxShadow: isSystemHealthy ? '0 0 6px #10b981' : 'none',
                }}
              />
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: isSystemHealthy ? '#059669' : '#d97706',
                }}
              >
                {systemHealthText}
              </span>
            </div>
          </div>
        ) : (
          <div
            onClick={onToggleCollapse}
            title={`${systemHealthText} (LangGraph v2.5)`}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '8px 0',
              cursor: 'pointer',
            }}
          >
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: isSystemHealthy ? '#10b981' : '#f59e0b',
                boxShadow: isSystemHealthy ? '0 0 8px #10b981' : 'none',
              }}
            />
          </div>
        )}
      </div>
    </aside>
  );
};
