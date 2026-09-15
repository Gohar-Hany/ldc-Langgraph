import React, { useState, useRef, useEffect } from 'react';
import { 
  RotateCcw, 
  ChevronDown, 
  PanelLeftOpen, 
  PanelLeftClose, 
  Check, 
  UserCheck,
  Plus
} from 'lucide-react';
import { UserRole, ROLE_DEFINITIONS } from '../types';

interface HeaderProps {
  currentRole: UserRole;
  onSelectRole: (role: UserRole) => void;
  onNewSession: () => void;
  language?: 'en' | 'ar';
  onToggleLanguage?: () => void;
  onToggleSidebar?: () => void;
  isSidebarCollapsed?: boolean;
  isMobile?: boolean;
  onOpenScenarios?: () => void;
  onOpenInfra?: () => void;
  selectedModel?: string;
  onSelectModel?: (model: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentRole,
  onSelectRole,
  onNewSession,
  onToggleSidebar,
  isSidebarCollapsed,
  isMobile = false,
}) => {
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const [isRotating, setIsRotating] = useState(false);
  const roleMenuRef = useRef<HTMLDivElement>(null);

  const roleInfo = ROLE_DEFINITIONS[currentRole];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (roleMenuRef.current && !roleMenuRef.current.contains(e.target as Node)) {
        setShowRoleMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNewSessionClick = () => {
    setIsRotating(true);
    onNewSession();
    setTimeout(() => setIsRotating(false), 500);
  };

  return (
    <header
      style={{
        height: isMobile ? '54px' : '60px',
        minHeight: isMobile ? '54px' : '60px',
        background: '#ffffff',
        borderBottom: '1px solid #e2e8f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: isMobile ? '0 12px' : '0 24px',
        zIndex: 30,
        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.02)',
      }}
    >
      {/* Left: Sidebar Toggle + Title + Subtitle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '8px' : '14px', minWidth: 0 }}>
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            title={isMobile ? 'Open Menu' : isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: isMobile ? '6px' : '7px',
              color: '#475569',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#f1f5f9';
              e.currentTarget.style.color = '#0f172a';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#f8fafc';
              e.currentTarget.style.color = '#475569';
            }}
          >
            {isMobile ? <PanelLeftOpen size={16} /> : isSidebarCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.25, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1
              style={{
                margin: 0,
                fontSize: isMobile ? '13.5px' : '15px',
                fontWeight: 800,
                color: '#0f172a',
                letterSpacing: '-0.02em',
                whiteSpace: 'nowrap',
              }}
            >
              {isMobile ? 'LDC AI Console' : 'LDC Enterprise AI Console'}
            </h1>

            {isMobile ? (
              <span
                title="Live Cloud Agent"
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#059669',
                  boxShadow: '0 0 5px #10b981',
                  flexShrink: 0,
                }}
              />
            ) : (
              <span
                style={{
                  fontSize: '10.5px',
                  fontWeight: 700,
                  color: '#059669',
                  background: '#ecfdf5',
                  border: '1px solid #a7f3d0',
                  padding: '1px 7px',
                  borderRadius: '9999px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  whiteSpace: 'nowrap',
                }}
              >
                <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#059669' }} />
                Live Cloud Agent
              </span>
            )}
          </div>

          <span className="hide-on-mobile" style={{ fontSize: '11px', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            Autonomous Tier-3 Cloud Infrastructure Support & LangGraph Orchestration
          </span>
        </div>
      </div>

      {/* Right: Clean, Uncluttered Controls (Role Selector + Premium New Session CTA) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '6px' : '10px', flexShrink: 0 }}>
        {/* 1. Role / Clearance Level Dropdown */}
        <div ref={roleMenuRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setShowRoleMenu(!showRoleMenu)}
            title={`Clearance Level: ${roleInfo.title} (${roleInfo.clearance})`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? '5px' : '8px',
              height: isMobile ? '34px' : '36px',
              padding: isMobile ? '0 8px' : '0 12px',
              borderRadius: '8px',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              color: '#0f172a',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#cbd5e1')}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#e2e8f0')}
          >
            <UserCheck size={14} color="#059669" />
            {!isMobile && <span>{roleInfo.title}</span>}
            <span
              style={{
                fontSize: '9.5px',
                fontWeight: 800,
                padding: '1px 5px',
                borderRadius: '4px',
                background: '#ecfdf5',
                color: '#047857',
                border: '1px solid #a7f3d0',
              }}
            >
              {roleInfo.clearance}
            </span>
            <ChevronDown size={11} color="#64748b" />
          </button>

          {showRoleMenu && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                width: isMobile ? '210px' : '240px',
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
                padding: '6px',
                zIndex: 50,
              }}
            >
              <div style={{ padding: '6px 8px', fontSize: '10.5px', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase' }}>
                RBAC Clearance Level
              </div>
              {(['customer', 'support_agent', 'senior_agent', 'admin'] as UserRole[]).map((roleKey) => {
                const info = ROLE_DEFINITIONS[roleKey];
                const isSelected = currentRole === roleKey;
                return (
                  <div
                    key={roleKey}
                    onClick={() => {
                      onSelectRole(roleKey);
                      setShowRoleMenu(false);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      background: isSelected ? '#f1f5f9' : 'transparent',
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.background = '#f8fafc';
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a' }}>{info.title}</div>
                      <div style={{ fontSize: '10px', color: '#64748b' }}>{info.description}</div>
                    </div>
                    {isSelected && <Check size={14} color="#059669" />}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 2. Premium New Session Button (Compact on mobile, full on desktop) */}
        <button
          onClick={handleNewSessionClick}
          title="Start fresh session (clears chat & resets LangGraph thread)"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            height: isMobile ? '34px' : '36px',
            width: isMobile ? '34px' : 'auto',
            padding: isMobile ? '0' : '0 16px',
            borderRadius: '8px',
            background: '#0f172a', // Corporate dark slate
            color: '#ffffff',
            border: '1px solid #1e293b',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 1px 3px rgba(15, 23, 42, 0.12)',
            transition: 'all 0.15s ease',
            whiteSpace: 'nowrap',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#1e293b';
            e.currentTarget.style.boxShadow = '0 2px 6px rgba(15, 23, 42, 0.2)';
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#0f172a';
            e.currentTarget.style.boxShadow = '0 1px 3px rgba(15, 23, 42, 0.12)';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          <RotateCcw
            size={13}
            style={{
              transition: 'transform 0.5s ease',
              transform: isRotating ? 'rotate(-360deg)' : 'rotate(0deg)',
            }}
          />
          {!isMobile && <span>New Session</span>}
        </button>
      </div>
    </header>
  );
};
