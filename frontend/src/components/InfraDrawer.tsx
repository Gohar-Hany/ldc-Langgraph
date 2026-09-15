import React, { useState } from 'react';
import { 
  X, 
  ShieldCheck, 
  Server, 
  Database, 
  Layers, 
  Cpu, 
  Search, 
  Zap, 
  Copy, 
  Check, 
  RefreshCw 
} from 'lucide-react';
import { UserRole, ROLE_DEFINITIONS, HealthReadyResponse } from '../types';

interface InfraDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentRole: UserRole;
  onSelectRole: (role: UserRole) => void;
  threadId: string;
  isCacheBypassed: boolean;
  onToggleCacheBypass: () => void;
  health: HealthReadyResponse | null;
  isLoadingHealth: boolean;
  onRefreshHealth: () => void;
  isMobile?: boolean;
}

export const InfraDrawer: React.FC<InfraDrawerProps> = ({
  isOpen,
  onClose,
  currentRole,
  onSelectRole,
  threadId,
  isCacheBypassed,
  onToggleCacheBypass,
  health,
  isLoadingHealth,
  onRefreshHealth,
  isMobile = false,
}) => {
  const [copiedThread, setCopiedThread] = useState(false);

  if (!isOpen) return null;

  const handleCopyThread = () => {
    navigator.clipboard.writeText(threadId);
    setCopiedThread(true);
    setTimeout(() => setCopiedThread(false), 2000);
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'ready':
      case 'healthy':
        return 'var(--status-success)';
      case 'fallback_mode':
        return 'var(--status-warning)';
      case 'degraded':
      case 'unconfigured':
        return 'var(--status-danger)';
      default:
        return 'var(--text-muted)';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        bottom: 0,
        width: isMobile ? '100vw' : '320px',
        maxWidth: '100vw',
        background: '#ffffff',
        boxShadow: '4px 0 20px rgba(0,0,0,0.1)',
        zIndex: 60,
        display: 'flex',
        flexDirection: 'column',
        borderRight: isMobile ? 'none' : '1px solid var(--border-light)',
        animation: 'slideInLeft 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: isMobile ? '10px 14px' : '12px 16px',
          borderBottom: '1px solid var(--border-light)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#f8fafc',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Server size={15} color="var(--text-primary)" />
          <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-primary)' }}>
            System & Governance
          </span>
        </div>

        <button onClick={onClose} style={{ padding: '4px', color: 'var(--text-muted)' }}>
          <X size={16} />
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Section 1: RBAC Persona */}
        <div>
          <div style={{ fontSize: '10.5px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Role-Based Access (RBAC)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {(Object.keys(ROLE_DEFINITIONS) as UserRole[]).map((role) => {
              const info = ROLE_DEFINITIONS[role];
              const isSelected = currentRole === role;
              return (
                <button
                  key={role}
                  onClick={() => onSelectRole(role)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '6px 8px',
                    borderRadius: 'var(--radius-sm)',
                    background: isSelected ? '#f1f5f9' : 'transparent',
                    border: isSelected ? '1px solid var(--border-strong)' : '1px solid transparent',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '9px', fontWeight: 800, padding: '1px 4px', borderRadius: '3px', background: isSelected ? 'var(--action-primary)' : '#e2e8f0', color: isSelected ? '#fff' : 'var(--text-secondary)' }}>
                      {info.clearance}
                    </span>
                    <span style={{ fontSize: '12px', fontWeight: isSelected ? 700 : 500, color: 'var(--text-primary)' }}>
                      {info.title}
                    </span>
                  </div>
                  {isSelected && <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--action-primary)' }} />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 2: Infrastructure Health */}
        <div style={{ border: '1px solid var(--border-light)', borderRadius: '6px', padding: '10px', background: '#f8fafc' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '10.5px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Infrastructure Health
            </span>
            <button onClick={onRefreshHealth} disabled={isLoadingHealth} style={{ color: 'var(--text-muted)' }}>
              <RefreshCw size={11} className={isLoadingHealth ? 'animate-spin' : ''} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', fontSize: '11.5px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Supabase PostgreSQL</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: getStatusColor(health?.dependencies?.supabase_postgresql?.status) }} />
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Online</span>
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Qdrant Vector DB</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: getStatusColor(health?.dependencies?.qdrant_vector_db?.status) }} />
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Ready</span>
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>LLM Orchestrator</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-success)' }} />
                <span style={{ fontSize: '10px', color: 'var(--status-success)', fontWeight: 600 }}>Active</span>
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Tavily External Search</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: getStatusColor(health?.dependencies?.tavily_external_search?.status) }} />
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Fallback</span>
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: Semantic Cache */}
        <div style={{ border: '1px solid var(--border-light)', borderRadius: '6px', padding: '10px', background: '#ffffff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>Vector Cache</span>
            <button
              onClick={onToggleCacheBypass}
              style={{
                fontSize: '10.5px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                background: isCacheBypassed ? '#fef3c7' : 'var(--status-success-bg)',
                color: isCacheBypassed ? '#b45309' : 'var(--status-success)',
                border: `1px solid ${isCacheBypassed ? '#fde68a' : 'var(--status-success-border)'}`,
              }}
            >
              {isCacheBypassed ? 'BYPASSED' : 'ACTIVE'}
            </button>
          </div>
        </div>

        {/* Section 4: Session Thread ID */}
        <div style={{ border: '1px solid var(--border-light)', borderRadius: '6px', padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10.5px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '220px' }}>
            {threadId}
          </span>
          <button onClick={handleCopyThread} style={{ padding: '2px', color: copiedThread ? 'var(--status-success)' : 'var(--text-muted)' }}>
            {copiedThread ? <Check size={13} /> : <Copy size={13} />}
          </button>
        </div>
      </div>
    </div>
  );
};
