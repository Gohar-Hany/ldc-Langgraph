import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Copy, 
  Check, 
  ChevronDown, 
  ChevronRight, 
  Bot, 
  User, 
  Maximize2, 
  Minimize2, 
  Zap, 
  Ticket, 
  Sparkles, 
  Globe, 
  Database,
  ArrowRight
} from 'lucide-react';
import { ChatMessage, UserRole, PipelineStageId, StageStatus } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';
import { HitlBanner } from './HitlBanner';
import { PipelineStepper } from './PipelineStepper';

interface ChatViewProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSendMessage: (text: string) => void;
  onNewSession: () => void;
  currentRole: UserRole;
  onElevateRole: () => void;
  onDecideApproval: (approved: boolean, notes: string) => Promise<void>;
  isDecidingApproval: boolean;
  activeThreadId: string;
  onOpenScenarios?: () => void;
  stageStatuses?: Record<PipelineStageId, StageStatus>;
  activeNodeName?: string;
  currentThought?: string;
  isMobile?: boolean;
}

const SUGGESTION_CHIPS = [
  {
    id: 'sla',
    title: 'Colocation & Power SLA',
    desc: 'Uptime guarantees, N+1 power redundancy, and Cairo DC specifications',
    prompt: "What are the power redundancy and uptime SLA specifications for Link Datacenter's Cairo facility?",
    icon: Database,
    bg: '#ecfdf5',
    border: '#a7f3d0',
    color: '#047857',
    hoverBg: '#d1fae5',
  },
  {
    id: 'quota',
    title: 'Storage Quota (HITL)',
    desc: 'Request 120GB storage expansion with supervisor authorization (HITL)',
    prompt: 'Request an immediate quota expansion of 120GB storage for customer account LDC-9921',
    icon: Zap,
    bg: '#fffbeb',
    border: '#fde68a',
    color: '#b45309',
    hoverBg: '#fef3c7',
  },
  {
    id: 'bgp',
    title: 'BGP Routing & Latency',
    desc: 'Check live BGP routing status, latency, and link health diagnostics',
    prompt: 'What is the current BGP routing status and any connectivity issues for our dedicated link?',
    icon: Globe,
    bg: '#eff6ff',
    border: '#bfdbfe',
    color: '#1d4ed8',
    hoverBg: '#dbeafe',
  },
  {
    id: 'tickets',
    title: 'Support Tickets & SLA',
    desc: 'Query customer support tickets and active service desk states',
    prompt: 'Show me all my open support tickets and their current status',
    icon: Ticket,
    bg: '#faf5ff',
    border: '#e9d5ff',
    color: '#6d28d9',
    hoverBg: '#f3e8ff',
  },
];

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  isStreaming,
  onSendMessage,
  onNewSession,
  currentRole,
  onElevateRole,
  onDecideApproval,
  isDecidingApproval,
  activeThreadId,
  stageStatuses,
  activeNodeName,
  currentThought,
  isMobile = false,
}) => {
  const [inputText, setInputText] = useState('');
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [expandedReasoning, setExpandedReasoning] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedThread, setCopiedThread] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!inputText.trim() || isStreaming) return;
    onSendMessage(inputText.trim());
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const toggleReasoning = (messageId: string) => {
    setExpandedReasoning((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCopyThreadId = () => {
    navigator.clipboard.writeText(activeThreadId);
    setCopiedThread(true);
    setTimeout(() => setCopiedThread(false), 2000);
  };

  const hasInput = inputText.trim().length > 0;

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        background: '#f1f5f9',
        padding: (isFocusMode || isMobile) ? '0' : '16px 20px',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Floating Centered Card Container */}
      <div
        style={{
          width: '100%',
          maxWidth: isFocusMode ? '100%' : '1020px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: '#ffffff',
          borderRadius: (isFocusMode || isMobile) ? '0' : '16px',
          border: (isFocusMode || isMobile) ? 'none' : '1px solid #e2e8f0',
          boxShadow: (isFocusMode || isMobile) ? 'none' : '0 4px 25px -4px rgba(15, 23, 42, 0.05)',
          overflow: 'hidden',
          transition: 'max-width 0.2s ease, border-radius 0.2s ease',
        }}
      >
        {/* 1. Chat Header: Agent Identity + Useful Controls */}
        <div
          style={{
            padding: isMobile ? '10px 12px' : '12px 20px',
            borderBottom: '1px solid #f1f5f9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#ffffff',
            flexShrink: 0,
            gap: '8px',
          }}
        >
          {/* Agent Avatar & Identity */}
          <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '8px' : '12px', minWidth: 0 }}>
            <div
              style={{
                width: isMobile ? '32px' : '36px',
                height: isMobile ? '32px' : '36px',
                borderRadius: '10px',
                background: '#064e3b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                boxShadow: '0 2px 6px rgba(6, 78, 59, 0.2)',
                flexShrink: 0,
              }}
            >
              <Bot size={isMobile ? 17 : 20} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: isMobile ? '13px' : '14px', fontWeight: 800, color: '#0f172a', whiteSpace: 'nowrap' }}>
                  Link Datacenter Support Agent
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    color: '#059669',
                    background: '#ecfdf5',
                    border: '1px solid #a7f3d0',
                    padding: '1px 5px',
                    borderRadius: '9999px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '3px',
                    flexShrink: 0,
                  }}
                >
                  <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#059669' }} />
                  Online
                </span>
              </div>
              <span className="hide-on-mobile" style={{ fontSize: '11px', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                Tier-3 Cloud Infrastructure Engineer · Colocation, SLA & Resource Automation
              </span>
            </div>
          </div>

          {/* Useful Controls: Thread ID Copy, Focus Mode */}
          <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '4px' : '8px', flexShrink: 0 }}>
            <button
              onClick={handleCopyThreadId}
              title={`LangGraph Thread ID: ${activeThreadId} (Click to copy)`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: isMobile ? '4px 8px' : '5px 10px',
                borderRadius: '8px',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                color: '#475569',
                fontSize: '11px',
                fontFamily: 'monospace',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#cbd5e1')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#e2e8f0')}
            >
              <span>{isMobile ? `ID: ${activeThreadId.slice(0, 8)}...` : `Thread: ${activeThreadId.slice(0, 16)}...`}</span>
              {copiedThread ? <Check size={11} color="#059669" /> : <Copy size={11} />}
            </button>

            <button
              onClick={() => setIsFocusMode(!isFocusMode)}
              title={isFocusMode ? 'Exit Focus Mode' : 'Enter Focus Mode'}
              className="hide-on-mobile"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '5px 10px',
                borderRadius: '8px',
                background: isFocusMode ? '#0f172a' : '#f8fafc',
                border: '1px solid #e2e8f0',
                color: isFocusMode ? '#ffffff' : '#64748b',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {isFocusMode ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
              <span>Focus Mode</span>
            </button>
          </div>
        </div>

        {/* 2. Embedded Slim Pipeline Stepper */}
        {stageStatuses && (
          <PipelineStepper
            stageStatuses={stageStatuses}
            activeNodeName={activeNodeName}
            currentThought={currentThought}
            isMobile={isMobile}
          />
        )}

        {/* 3. Messages Stream Scroll Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: isMobile ? '14px 12px' : '24px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: isMobile ? '12px' : '18px',
            background: '#ffffff',
          }}
        >
          {/* A. Vibrant Starter Grid in Empty State */}
          {messages.length === 0 ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                margin: 'auto',
                maxWidth: '780px',
                width: '100%',
                padding: isMobile ? '10px 0 16px 0' : '20px 0',
                gap: isMobile ? '16px' : '22px',
              }}
            >
              {/* Centered Agent Greeting */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '8px' }}>
                <div
                  style={{
                    width: isMobile ? '40px' : '48px',
                    height: isMobile ? '40px' : '48px',
                    borderRadius: '12px',
                    background: '#064e3b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#ffffff',
                    boxShadow: '0 4px 14px rgba(6, 78, 59, 0.2)',
                  }}
                >
                  <Bot size={isMobile ? 22 : 26} />
                </div>

                <h2 style={{ margin: 0, fontSize: isMobile ? '15px' : '17px', fontWeight: 800, color: '#0f172a', letterSpacing: '-0.02em' }}>
                  Link Datacenter Cloud Assistant
                </h2>

                <p style={{ margin: 0, fontSize: isMobile ? '12px' : '13px', color: '#64748b', maxWidth: '520px', lineHeight: 1.5 }}>
                  Autonomous Tier-3 Infrastructure Engineer. Select a starter inquiry below or type your message.
                </p>
              </div>

              {/* Vibrant Starter Action Cards (1 col on mobile, 2 col on desktop) */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)',
                  gap: isMobile ? '10px' : '12px',
                  width: '100%',
                }}
              >
                {SUGGESTION_CHIPS.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={item.id}
                      onClick={() => onSendMessage(item.prompt)}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: isMobile ? '10px' : '12px',
                        padding: isMobile ? '12px 14px' : '14px 16px',
                        borderRadius: '10px',
                        background: '#ffffff',
                        border: `1px solid ${item.border}`,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.02)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = item.bg;
                        e.currentTarget.style.borderColor = item.color;
                        e.currentTarget.style.boxShadow = '0 4px 14px rgba(0, 0, 0, 0.06)';
                        e.currentTarget.style.transform = 'translateY(-2px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = '#ffffff';
                        e.currentTarget.style.borderColor = item.border;
                        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.02)';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '8px',
                          background: item.bg,
                          color: item.color,
                          border: `1px solid ${item.border}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          marginTop: '1px',
                        }}
                      >
                        <Icon size={16} color={item.color} />
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                            {item.title}
                          </span>
                          <ArrowRight size={13} color={item.color} />
                        </div>
                        <p style={{ margin: '3px 0 0 0', fontSize: '11.5px', color: '#64748b', lineHeight: 1.4 }}>
                          {item.desc}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* B. Active Messages Stream */
            messages.map((message) => {
              const isUser = message.sender === 'user';
              const isSystem = message.sender === 'system';
              const reasoningText = message.thoughts && message.thoughts.length > 0 ? message.thoughts.join('\n') : undefined;

              if (isSystem) {
                return (
                  <div
                    key={message.id}
                    style={{
                      alignSelf: 'center',
                      fontSize: '11px',
                      fontWeight: 600,
                      color: '#64748b',
                      background: '#f1f5f9',
                      padding: '4px 12px',
                      borderRadius: '9999px',
                      border: '1px solid #e2e8f0',
                      margin: '4px 0',
                    }}
                  >
                    {message.text}
                  </div>
                );
              }

              return (
                <div
                  key={message.id}
                  style={{
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    gap: isMobile ? '8px' : '12px',
                    alignItems: 'flex-start',
                    maxWidth: '850px',
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                    width: '100%',
                  }}
                >
                  {/* Bot or User Avatar */}
                  <div
                    style={{
                      width: isMobile ? '28px' : '32px',
                      height: isMobile ? '28px' : '32px',
                      borderRadius: '8px',
                      background: isUser ? '#0f172a' : '#ecfdf5',
                      border: isUser ? 'none' : '1px solid #a7f3d0',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: isUser ? '#ffffff' : '#059669',
                      flexShrink: 0,
                      marginTop: '2px',
                    }}
                  >
                    {isUser ? <User size={isMobile ? 14 : 16} /> : <Bot size={isMobile ? 15 : 18} />}
                  </div>

                  {/* Message Bubble Container */}
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      maxWidth: isUser ? (isMobile ? '86%' : '75%') : (isMobile ? '92%' : '85%'),
                    }}
                  >
                    {/* Collapsible Chain of Thought */}
                    {!isUser && reasoningText && (
                      <div
                        style={{
                          background: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: '8px',
                          overflow: 'hidden',
                          marginBottom: '4px',
                        }}
                      >
                        <button
                          onClick={() => toggleReasoning(message.id)}
                          style={{
                            width: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '6px 12px',
                            background: 'transparent',
                            border: 'none',
                            fontSize: '11px',
                            fontWeight: 600,
                            color: '#475569',
                            cursor: 'pointer',
                          }}
                        >
                          <Sparkles size={12} color="#059669" />
                          <span>خطوات التحليل والمعالجة الذكية · System Reasoning</span>
                          {expandedReasoning[message.id] ? (
                            <ChevronDown size={12} style={{ marginLeft: 'auto' }} />
                          ) : (
                            <ChevronRight size={12} style={{ marginLeft: 'auto' }} />
                          )}
                        </button>

                        {expandedReasoning[message.id] && (
                          <div
                            style={{
                              padding: '8px 12px',
                              borderTop: '1px solid #e2e8f0',
                              fontSize: '11.5px',
                              color: '#334155',
                              background: '#fafafa',
                              maxHeight: '180px',
                              overflowY: 'auto',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '4px',
                            }}
                          >
                            {reasoningText.split('\n').filter((l) => l.trim().length > 0).map((line, lIdx) => (
                              <div key={lIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                                <span style={{ color: '#059669', fontSize: '10px', marginTop: '1px', flexShrink: 0 }}>●</span>
                                <span style={{ lineHeight: 1.45 }}>{line}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Message Bubble */}
                    <div
                      style={{
                        padding: isMobile ? '10px 12px' : '12px 16px',
                        borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                        background: isUser ? '#0f172a' : '#f8fafc',
                        color: isUser ? '#ffffff' : '#0f172a',
                        border: isUser ? 'none' : '1px solid #e2e8f0',
                        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.03)',
                        fontSize: isMobile ? '13px' : '13.5px',
                        lineHeight: 1.55,
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                      }}
                    >
                      {isUser ? (
                        message.text
                      ) : (
                        <MarkdownRenderer content={message.text} />
                      )}
                    </div>

                    {/* Timestamp & Copy Action */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        alignSelf: isUser ? 'flex-end' : 'flex-start',
                        fontSize: '10.5px',
                        color: '#94a3b8',
                      }}
                    >
                      <span>
                        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>

                      {!isUser && (
                        <button
                          onClick={() => handleCopy(message.text, message.id)}
                          title="Copy response"
                          style={{
                            background: 'transparent',
                            border: 'none',
                            padding: '2px',
                            color: '#94a3b8',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                        >
                          {copiedId === message.id ? <Check size={11} color="#059669" /> : <Copy size={11} />}
                        </button>
                      )}
                    </div>

                    {/* Sensitive Action / HITL Banner */}
                    {message.approvalDetails && (
                      <div style={{ marginTop: '4px' }}>
                        <HitlBanner
                          threadId={activeThreadId}
                          approvalDetails={message.approvalDetails}
                          approvalStatus={message.approvalStatus}
                          currentRole={currentRole}
                          onElevateRole={onElevateRole}
                          onDecide={onDecideApproval}
                          isDeciding={isDecidingApproval}
                        />
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 4. Bottom Area: Vibrant, High-Contrast Suggestion Chips & Modern Input */}
        <div
          style={{
            padding: isMobile ? '8px 10px calc(8px + env(safe-area-inset-bottom, 0px)) 10px' : '10px 20px 16px 20px',
            borderTop: '1px solid #f1f5f9',
            background: '#ffffff',
            display: 'flex',
            flexDirection: 'column',
            gap: isMobile ? '6px' : '9px',
            flexShrink: 0,
          }}
        >
          {/* Vibrant, High-Contrast Colored Suggestion Chips */}
          <div
            className="touch-scroll-x"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? '6px' : '8px',
              paddingBottom: '2px',
              width: '100%',
            }}
          >
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#475569',
                whiteSpace: 'nowrap',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                flexShrink: 0,
              }}
            >
              <Sparkles size={12} color="#059669" />
              Try:
            </span>

            {SUGGESTION_CHIPS.map((chip) => {
              const Icon = chip.icon;
              return (
                <button
                  key={chip.id}
                  onClick={() => onSendMessage(chip.prompt)}
                  disabled={isStreaming}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    fontSize: isMobile ? '11px' : '11.5px',
                    fontWeight: 600,
                    color: chip.color,
                    background: chip.bg,
                    border: `1px solid ${chip.border}`,
                    borderRadius: '9999px',
                    padding: isMobile ? '3px 10px' : '4px 12px',
                    whiteSpace: 'nowrap',
                    cursor: isStreaming ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.02)',
                    flexShrink: 0,
                  }}
                  onMouseEnter={(e) => {
                    if (!isStreaming) {
                      e.currentTarget.style.background = chip.hoverBg;
                      e.currentTarget.style.borderColor = chip.color;
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.06)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isStreaming) {
                      e.currentTarget.style.background = chip.bg;
                      e.currentTarget.style.borderColor = chip.border;
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.02)';
                    }
                  }}
                >
                  <Icon size={12} color={chip.color} />
                  <span>{chip.title}</span>
                </button>
              );
            })}
          </div>

          {/* Clean Modern Input Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? '8px' : '10px',
              background: '#ffffff',
              border: hasInput ? '1.5px solid #064e3b' : '1px solid #cbd5e1',
              borderRadius: '24px',
              padding: isMobile ? '4px 6px 4px 14px' : '6px 8px 6px 16px',
              boxShadow: hasInput ? '0 0 0 3px rgba(6, 78, 59, 0.08)' : '0 1px 3px rgba(0, 0, 0, 0.03)',
              transition: 'all 0.15s ease',
            }}
          >
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`;
              }}
              onKeyDown={handleKeyDown}
              placeholder={isMobile ? "Ask LDC Agent..." : "Ask LDC Agent (e.g. colocation SLA, expand quota, BGP routing)..."}
              rows={1}
              disabled={isStreaming}
              style={{
                flex: 1,
                border: 'none',
                padding: '6px 0',
                fontSize: isMobile ? '13px' : '13.5px',
                lineHeight: 1.4,
                resize: 'none',
                maxHeight: '100px',
                background: 'transparent',
                outline: 'none',
                color: '#0f172a',
              }}
            />

            <button
              onClick={handleSend}
              disabled={!hasInput || isStreaming}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: isMobile ? '7px 12px' : '8px 18px',
                borderRadius: '18px',
                background: hasInput && !isStreaming ? '#064e3b' : '#cbd5e1',
                color: '#ffffff',
                border: 'none',
                fontSize: isMobile ? '12px' : '12.5px',
                fontWeight: 700,
                cursor: hasInput && !isStreaming ? 'pointer' : 'not-allowed',
                transition: 'all 0.15s ease',
                flexShrink: 0,
              }}
            >
              <span>Send</span>
              <Send size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
