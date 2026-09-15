import React from 'react';
import { 
  ChevronRight, 
  Sparkles,
  Check,
  AlertTriangle,
  X
} from 'lucide-react';
import { PipelineStageId, StageStatus } from '../types';

interface StageConfig {
  id: PipelineStageId;
  stepNum: number;
  label: string;
}

const STAGES: StageConfig[] = [
  { id: 'guardrail_in', stepNum: 1, label: 'Guardrail In' },
  { id: 'router_node', stepNum: 2, label: 'Semantic Router' },
  { id: 'cloud_rag_tools', stepNum: 3, label: 'RAG / Cloud Tools' },
  { id: 'hitl_gate', stepNum: 4, label: 'HITL Gate' },
  { id: 'synthesizer', stepNum: 5, label: 'Synthesizer' },
];

interface PipelineStepperProps {
  stageStatuses: Record<PipelineStageId, StageStatus>;
  activeNodeName?: string;
  currentThought?: string;
  isMobile?: boolean;
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  stageStatuses,
  activeNodeName,
  currentThought,
  isMobile = false,
}) => {
  return (
    <div
      style={{
        height: '32px',
        minHeight: '32px',
        background: '#ffffff',
        borderBottom: '1px solid var(--border-light)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: isMobile ? '0 10px' : '0 20px',
        fontSize: '11px',
        zIndex: 10,
        overflow: 'hidden',
      }}
    >
      {/* Slim Horizontal Breadcrumb */}
      <div
        className="touch-scroll-x"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: isMobile ? '4px' : '6px',
          width: isMobile ? '100%' : 'auto',
          flexShrink: 0,
        }}
      >
        {STAGES.map((stage, idx) => {
          const status = stageStatuses[stage.id] || 'idle';

          let dotColor = '#cbd5e1'; // gray/pending
          let textColor = '#64748b';
          let isRunning = false;
          let isDone = false;
          let isPaused = false;
          let isErr = false;

          if (status === 'running') {
            dotColor = 'var(--ldc-green)';
            textColor = 'var(--ldc-green-dark)';
            isRunning = true;
          } else if (status === 'completed') {
            dotColor = '#16a34a';
            textColor = 'var(--text-primary)';
            isDone = true;
          } else if (status === 'interrupted') {
            dotColor = '#d97706';
            textColor = '#b45309';
            isPaused = true;
          } else if (status === 'error') {
            dotColor = '#dc2626';
            textColor = '#dc2626';
            isErr = true;
          }

          return (
            <React.Fragment key={stage.id}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  whiteSpace: 'nowrap',
                  fontWeight: isRunning || isDone ? 700 : 500,
                  color: textColor,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: isRunning ? 'var(--status-success-bg)' : (isPaused ? 'var(--status-warning-bg)' : 'transparent'),
                }}
              >
                {/* Dot / Icon */}
                {isDone ? (
                  <span
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: '#dcfce7',
                      color: '#16a34a',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '9px',
                    }}
                  >
                    <Check size={8} strokeWidth={3} />
                  </span>
                ) : isPaused ? (
                  <span
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: '#fef3c7',
                      color: '#d97706',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '9px',
                    }}
                  >
                    <AlertTriangle size={8} strokeWidth={3} />
                  </span>
                ) : isErr ? (
                  <span
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: '#fee2e2',
                      color: '#dc2626',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '9px',
                    }}
                  >
                    <X size={8} strokeWidth={3} />
                  </span>
                ) : (
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: dotColor,
                    }}
                    className={isRunning ? 'animate-pulse-glow' : ''}
                  />
                )}

                <span>{stage.stepNum}. {stage.label}</span>
              </div>

              {idx < STAGES.length - 1 && (
                <ChevronRight size={11} color="#cbd5e1" style={{ flexShrink: 0 }} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Slim Realtime Thought Ticker */}
      {(currentThought || activeNodeName) && !isMobile && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--text-secondary)',
            fontSize: '11px',
            maxWidth: '450px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          <Sparkles size={12} color="var(--ldc-green)" style={{ flexShrink: 0 }} />
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
            {activeNodeName ? `[${activeNodeName}]` : 'Running:'}
          </span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-muted)' }}>
            {currentThought}
          </span>
        </div>
      )}
    </div>
  );
};
