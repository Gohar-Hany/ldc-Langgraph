import React, { useState } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Lock, 
  ArrowUpRight, 
  ChevronDown, 
  ChevronRight,
  Code,
  Check
} from 'lucide-react';
import { UserRole } from '../types';

interface HitlBannerProps {
  threadId: string;
  approvalDetails: {
    action?: string;
    tool?: string;
    payload?: Record<string, any>;
    reason?: string;
    reviewer_notes?: string;
    decided_by?: string;
    [key: string]: any;
  };
  approvalStatus?: 'PENDING' | 'APPROVED' | 'REJECTED' | null;
  currentRole: UserRole;
  onElevateRole: () => void;
  onDecide: (approved: boolean, notes: string) => Promise<void>;
  isDeciding: boolean;
}

export const HitlBanner: React.FC<HitlBannerProps> = ({
  threadId,
  approvalDetails,
  approvalStatus = 'PENDING',
  currentRole,
  onElevateRole,
  onDecide,
  isDeciding,
}) => {
  const [notes, setNotes] = useState('');
  const [showDetails, setShowDetails] = useState(false);

  const isAuthorized = currentRole === 'senior_agent' || currentRole === 'admin';
  const isDecided = approvalStatus === 'APPROVED' || approvalStatus === 'REJECTED';
  const isApproved = approvalStatus === 'APPROVED';

  const actionName = approvalDetails.action || 'sensitive_operation';
  const reason = approvalDetails.reason || 'Operation requires supervisor authorization.';
  const payload = approvalDetails.payload || {};
  const decidedBy = approvalDetails.decided_by || 'Senior Agent';
  const reviewerNotes = approvalDetails.reviewer_notes || 'Approved per SLA policy.';

  // Extract amount if present in payload
  const amountStr = payload.amount ? `$${payload.amount}` : '';

  // STATE A: DECIDED (Ultra-compact 1-2 line summary card with ZERO repetition)
  if (isDecided) {
    return (
      <div
        style={{
          margin: '6px 0',
          borderRadius: 'var(--radius-sm)',
          background: isApproved ? '#f0fdf4' : '#fef2f2',
          border: isApproved ? '1px solid #bbf7d0' : '1px solid #fecaca',
          padding: '8px 12px',
          fontSize: '12.5px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isApproved ? (
              <Check size={14} color="#16a34a" strokeWidth={3} />
            ) : (
              <XCircle size={14} color="#dc2626" />
            )}
            <span style={{ fontWeight: 700, color: isApproved ? '#166534' : '#991b1b' }}>
              {isApproved ? `Refund ${amountStr} approved by ${decidedBy}` : `Operation rejected by ${decidedBy}`}
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
              &bull; Ref: REF-20260912
            </span>
          </div>

          <button
            onClick={() => setShowDetails(!showDetails)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              fontSize: '11px',
              fontWeight: 600,
              color: isApproved ? '#15803d' : '#991b1b',
              background: 'transparent',
            }}
          >
            <span>{showDetails ? 'Hide Audit' : 'Audit Details'}</span>
            {showDetails ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        </div>

        {/* Collapsible Details Drawer */}
        {showDetails && (
          <div
            style={{
              marginTop: '8px',
              paddingTop: '8px',
              borderTop: isApproved ? '1px solid #bbf7d0' : '1px solid #fecaca',
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            <div>
              <strong>Supervisor Note:</strong> "{reviewerNotes}"
            </div>
            <div>
              <strong>Audit Trail:</strong> Written to Supabase PostgreSQL &bull; Action: <code>{actionName}</code>
            </div>
            <details style={{ marginTop: '4px' }}>
              <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '11px' }}>View Payload Parameters</summary>
              <pre style={{ background: '#0f172a', color: '#f8fafc', padding: '6px', borderRadius: '4px', fontSize: '10.5px', marginTop: '4px' }}>
                {JSON.stringify(payload, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    );
  }

  // STATE B: PENDING (Compact 2-line action card)
  return (
    <div
      style={{
        margin: '8px 0',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--status-warning-bg)',
        border: '1.5px solid var(--status-warning)',
        padding: '10px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      {/* Line 1: Clear summary */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldAlert size={15} color="#d97706" />
          <span style={{ fontSize: '13px', fontWeight: 800, color: '#92400e' }}>
            Action Required: {actionName} {amountStr && `(${amountStr})`}
          </span>
          <span style={{ fontSize: '11px', color: '#b45309' }}>
            &bull; {reason}
          </span>
        </div>

        <span style={{ fontSize: '10.5px', fontFamily: 'var(--font-mono)', color: '#b45309' }}>
          {threadId}
        </span>
      </div>

      {/* Line 2: Actions */}
      {isAuthorized ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Audit notes (e.g. SLA breach verified)..."
            style={{
              flex: 1,
              padding: '5px 8px',
              fontSize: '11.5px',
              borderRadius: '4px',
              border: '1px solid #fde68a',
              background: '#ffffff',
            }}
          />

          <button
            onClick={() => onDecide(false, notes || 'Rejected by supervisor.')}
            disabled={isDeciding}
            style={{
              padding: '5px 10px',
              borderRadius: '4px',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              color: '#dc2626',
              fontSize: '11.5px',
              fontWeight: 700,
            }}
          >
            Reject
          </button>

          <button
            onClick={() => onDecide(true, notes || 'Approved by supervisor.')}
            disabled={isDeciding}
            style={{
              padding: '5px 12px',
              borderRadius: '4px',
              background: 'var(--status-success)',
              color: '#ffffff',
              fontSize: '11.5px',
              fontWeight: 700,
            }}
          >
            {isDeciding ? 'Resuming...' : 'Approve & Resume'}
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '11.5px', color: '#92400e' }}>
            Your role ({currentRole}) cannot authorize financial mutations.
          </span>
          <button
            onClick={onElevateRole}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
              borderRadius: '4px',
              background: 'var(--status-warning)',
              color: '#ffffff',
              fontSize: '11px',
              fontWeight: 700,
            }}
          >
            <span>Switch to Senior Agent (L3)</span>
            <ArrowUpRight size={11} />
          </button>
        </div>
      )}
    </div>
  );
};
