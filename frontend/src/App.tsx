import React, { useState, useEffect, useCallback } from 'react';
import { 
  UserRole, 
  PipelineStageId, 
  StageStatus, 
  ChatMessage, 
  TicketItem, 
  HealthReadyResponse, 
  DemoScenario 
} from './types';
import { apiService } from './services/api';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatView } from './components/ChatView';
import { ScenariosDrawer } from './components/ScenariosDrawer';
import { InfraDrawer } from './components/InfraDrawer';

function generateThreadId(): string {
  const timestamp = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 7);
  return `thread_ldc_${timestamp}_${rand}`;
}

const INITIAL_STAGES: Record<PipelineStageId, StageStatus> = {
  guardrail_in: 'idle',
  router_node: 'idle',
  cloud_rag_tools: 'idle',
  hitl_gate: 'idle',
  synthesizer: 'idle',
};

export const App: React.FC = () => {
  // Session & Auth
  const [threadId, setThreadId] = useState<string>(generateThreadId);
  const [currentRole, setCurrentRole] = useState<UserRole>('customer');
  const [isCacheBypassed, setIsCacheBypassed] = useState<boolean>(false);
  const [language, setLanguage] = useState<'en' | 'ar'>('en');
  const [selectedModel, setSelectedModel] = useState<string>('Gemini 2.5 Pro');

  // Navigation & Sidebar Layout
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [isMobile, setIsMobile] = useState<boolean>(() => typeof window !== 'undefined' && window.innerWidth <= 768);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [activeNav, setActiveNav] = useState<string>('chat');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      if (!mobile) {
        setIsMobileSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Slide-over Drawer States (Off-canvas, opened on demand)
  const [isScenariosOpen, setIsScenariosOpen] = useState<boolean>(false);
  const [isInfraOpen, setIsInfraOpen] = useState<boolean>(false);
  const [drawerTab, setDrawerTab] = useState<'scenarios' | 'tickets'>('scenarios');

  // Messages & Stream State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isDecidingApproval, setIsDecidingApproval] = useState<boolean>(false);

  // Slim Stepper State
  const [stageStatuses, setStageStatuses] = useState<Record<PipelineStageId, StageStatus>>(INITIAL_STAGES);
  const [activeNodeName, setActiveNodeName] = useState<string>('');
  const [currentThought, setCurrentThought] = useState<string>('');

  // Health & Tickets State
  const [health, setHealth] = useState<HealthReadyResponse | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState<boolean>(false);
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [isLoadingTickets, setIsLoadingTickets] = useState<boolean>(false);

  const mapNodeToStage = (nodeName: string): PipelineStageId => {
    if (nodeName.includes('receive_message')) return 'guardrail_in';
    if (nodeName.includes('cache') || nodeName.includes('classify') || nodeName.includes('router')) return 'router_node';
    if (nodeName.includes('rag') || nodeName.includes('ticket') || nodeName.includes('search') || nodeName.includes('database')) return 'cloud_rag_tools';
    if (nodeName.includes('sensitive') || nodeName.includes('interrupt')) return 'hitl_gate';
    return 'synthesizer';
  };

  // 1. Initialize Auth Token on role change or mount
  const switchRole = useCallback(async (newRole: UserRole) => {
    try {
      setCurrentRole(newRole);
      await apiService.fetchToken(newRole);
      loadTickets(newRole !== 'customer');
    } catch (err) {
      console.error('Failed to switch role token:', err);
    }
  }, []);

  useEffect(() => {
    switchRole(currentRole);
  }, []);

  // 2. Poll Health Readiness every 25s
  const fetchHealth = useCallback(async () => {
    setIsLoadingHealth(true);
    try {
      const data = await apiService.getHealthReady();
      setHealth(data);
    } catch (err) {
      console.warn('Health check unavailable:', err);
    } finally {
      setIsLoadingHealth(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 25000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // 3. Load Tickets
  const loadTickets = useCallback(async (isAgentOrAdmin?: boolean) => {
    setIsLoadingTickets(true);
    try {
      const isElevated = isAgentOrAdmin !== undefined ? isAgentOrAdmin : (currentRole !== 'customer');
      const list = await apiService.getTickets(isElevated);
      setTickets(list);
    } catch (err) {
      console.warn('Failed to load tickets:', err);
    } finally {
      setIsLoadingTickets(false);
    }
  }, [currentRole]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  // 4. Reset Session Handler
  const handleNewSession = () => {
    const newThread = generateThreadId();
    setThreadId(newThread);
    setMessages([]);
    setStageStatuses(INITIAL_STAGES);
    setActiveNodeName('');
    setCurrentThought('');
  };

  // 5. Send Message Stream Handler
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);

    // Reset pipeline to pending
    setStageStatuses({
      guardrail_in: 'running',
      router_node: 'idle',
      cloud_rag_tools: 'idle',
      hitl_gate: 'idle',
      synthesizer: 'idle',
    });
    setActiveNodeName('receive_message');
    setCurrentThought('Validating input safety and session parameters...');

    const assistantMsgId = `asst_${Date.now()}`;
    let assistantContent = '';

    setMessages((prev) => [
      ...prev,
      {
        id: assistantMsgId,
        sender: 'agent',
        text: '',
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      await apiService.streamChat({
        message: text,
        threadId: threadId,
        bypassCache: isCacheBypassed,
        onStep: (data: any) => {
          const nodeName = data?.node || data?.step_name || '';
          const stage = mapNodeToStage(nodeName);
          setActiveNodeName(nodeName);
          setStageStatuses((prev) => ({
            ...prev,
            [stage]: 'running',
          }));
        },
        onToken: (token: string) => {
          assistantContent += token;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, text: assistantContent } : m
            )
          );
        },
        onThought: (thought: string) => {
          setCurrentThought(thought);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, thoughts: [...(m.thoughts || []), thought] }
                : m
            )
          );
        },
        onInterrupt: (interruptData: any) => {
          setStageStatuses((prev) => ({
            ...prev,
            hitl_gate: 'interrupted',
          }));
          setActiveNodeName('human_in_the_loop_gate');
          setCurrentThought('Operation paused: Supervisor approval required.');

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    text:
                      m.text ||
                      '⚠️ **Sensitive Operation Detected**: This action requires authorization from a Senior Agent or Administrator.',
                    approvalRequired: true,
                    approvalStatus: 'PENDING',
                    approvalDetails: interruptData?.approval_details || interruptData || {
                      action: 'sensitive_operation',
                      reason: 'Operation requires supervisor clearance.',
                      payload: interruptData?.payload || {},
                    },
                  }
                : m
            )
          );
        },
        onDone: () => {
          setStageStatuses((prev) => ({
            ...prev,
            synthesizer: 'completed',
          }));
          setActiveNodeName('');
          setCurrentThought('');
        },
        onError: (errMsg: string) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    text: m.text
                      ? `${m.text}\n\n❌ **Error encountered:** ${errMsg}`
                      : `❌ **Error encountered:** ${errMsg}`,
                  }
                : m
            )
          );
        },
      });

      setStageStatuses((prev) => ({
        ...prev,
        synthesizer: 'completed',
      }));
      setActiveNodeName('');
      setCurrentThought('');
    } catch (err: any) {
      console.error('Stream failure, attempting fallback:', err);
      try {
        const fallbackRes = await apiService.sendChatFallback({
          message: text,
          threadId: threadId,
          bypassCache: isCacheBypassed,
        });

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  text: fallbackRes.response,
                  thoughts: fallbackRes.reasoning ? [fallbackRes.reasoning] : [],
                }
              : m
          )
        );
        setStageStatuses({
          guardrail_in: 'completed',
          router_node: 'completed',
          cloud_rag_tools: 'completed',
          hitl_gate: 'completed',
          synthesizer: 'completed',
        });
      } catch (fallbackErr: any) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  text: `❌ Communication failed: ${fallbackErr.message || 'Service temporarily unreachable'}`,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
    }
  };

  // 6. Handle In-place HITL Decision
  const handleDecideApproval = async (approved: boolean, notes: string) => {
    setIsDecidingApproval(true);
    try {
      const res = await apiService.decideApproval(threadId, approved, notes);

      setMessages((prev) =>
        prev.map((m) => {
          if (m.approvalDetails) {
            return {
              ...m,
              text:
                res?.response ||
                (approved
                  ? '✅ **Operation Approved & Executed**: The storage quota has been updated in the cloud infrastructure.'
                  : '🚫 **Operation Rejected**: The supervisor rejected this action. No changes made.'),
              approvalStatus: approved ? 'APPROVED' : 'REJECTED',
              approvalDetails: {
                ...m.approvalDetails,
                reviewer_notes: notes,
                decided_by: currentRole === 'senior_agent' ? 'Senior Agent' : 'Administrator',
              },
            };
          }
          return m;
        })
      );

      setStageStatuses((prev) => ({
        ...prev,
        hitl_gate: 'completed',
        synthesizer: 'completed',
      }));
      setActiveNodeName('handle_sensitive_operation');
      setCurrentThought(approved ? 'Operation approved and executed.' : 'Operation aborted per supervisor.');

      loadTickets();
    } catch (err: any) {
      alert(`Approval submission failed: ${err.message}`);
    } finally {
      setIsDecidingApproval(false);
    }
  };

  // 7. Navigation Selector
  const handleSelectNav = (navId: string) => {
    setActiveNav(navId);
    if (isMobile) {
      setIsMobileSidebarOpen(false);
    }
    if (navId === 'scenarios') {
      setDrawerTab('scenarios');
      setIsScenariosOpen(true);
      setIsInfraOpen(false);
    } else if (navId === 'system') {
      setIsInfraOpen(true);
      setIsScenariosOpen(false);
    } else if (navId === 'tickets') {
      setDrawerTab('tickets');
      setIsScenariosOpen(true);
      setIsInfraOpen(false);
    } else if (navId === 'chat') {
      setIsScenariosOpen(false);
      setIsInfraOpen(false);
    }
  };

  const handleToggleSidebar = () => {
    if (isMobile) {
      setIsMobileSidebarOpen((prev) => !prev);
    } else {
      setIsSidebarCollapsed((prev) => !prev);
    }
  };

  // 8. Scenario Selection Handler
  const handleSelectScenario = (scenario: DemoScenario) => {
    if (currentRole !== scenario.targetRole) {
      switchRole(scenario.targetRole);
    }
    handleSendMessage(scenario.prompt);
    if (isMobile) {
      setIsScenariosOpen(false);
    }
  };

  // 9. Create Ticket
  const handleCreateTicket = async (payload: { title: string; description: string; priority: string; category: string }) => {
    await apiService.createTicket(payload);
    await loadTickets();
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'row',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        background: '#f1f5f9',
        position: 'relative',
      }}
    >
      {/* Mobile Backdrop for Sidebar */}
      {isMobile && isMobileSidebarOpen && (
        <div
          onClick={() => setIsMobileSidebarOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            backdropFilter: 'blur(2px)',
            zIndex: 90,
            animation: 'fadeIn 0.2s ease',
          }}
        />
      )}

      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
        activeNav={activeNav}
        onSelectNav={handleSelectNav}
        scenariosCount={8}
        openTicketsCount={tickets.length}
        systemHealthText={health?.status === 'ready' ? 'System Operational' : 'System Degraded'}
        isSystemHealthy={health?.status === 'ready'}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        isMobile={isMobile}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* 2. Main Content Column */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          height: '100vh',
          width: isMobile ? '100vw' : 'auto',
          minWidth: 0,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Top Header */}
        <Header
          currentRole={currentRole}
          onSelectRole={switchRole}
          onNewSession={handleNewSession}
          language={language}
          onToggleLanguage={() => setLanguage(language === 'en' ? 'ar' : 'en')}
          onToggleSidebar={handleToggleSidebar}
          isSidebarCollapsed={isSidebarCollapsed}
          isMobile={isMobile}
          onOpenScenarios={() => {
            setDrawerTab('scenarios');
            setIsScenariosOpen(true);
          }}
          onOpenInfra={() => setIsInfraOpen(true)}
          selectedModel={selectedModel}
          onSelectModel={setSelectedModel}
        />

        {/* Workspace: Floating Centered Chat Card Hero */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
          <ChatView
            messages={messages}
            isStreaming={isStreaming}
            onSendMessage={handleSendMessage}
            onNewSession={handleNewSession}
            currentRole={currentRole}
            onElevateRole={() => switchRole('senior_agent')}
            onDecideApproval={handleDecideApproval}
            isDecidingApproval={isDecidingApproval}
            activeThreadId={threadId}
            onOpenScenarios={() => {
              setDrawerTab('scenarios');
              setIsScenariosOpen(true);
            }}
            stageStatuses={stageStatuses}
            activeNodeName={activeNodeName}
            currentThought={currentThought}
            isMobile={isMobile}
          />

          {/* Mobile Backdrop for Drawers */}
          {isMobile && (isScenariosOpen || isInfraOpen) && (
            <div
              onClick={() => {
                setIsScenariosOpen(false);
                setIsInfraOpen(false);
              }}
              style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(15, 23, 42, 0.45)',
                backdropFilter: 'blur(2px)',
                zIndex: 55,
                animation: 'fadeIn 0.2s ease',
              }}
            />
          )}

          {/* Slide-over Drawer: Scenarios & Hub (Right) */}
          <ScenariosDrawer
            isOpen={isScenariosOpen}
            onClose={() => {
              setIsScenariosOpen(false);
              setActiveNav('chat');
            }}
            currentRole={currentRole}
            onSelectScenario={handleSelectScenario}
            onSelectRole={switchRole}
            tickets={tickets}
            isLoadingTickets={isLoadingTickets}
            onRefreshTickets={() => loadTickets()}
            onCreateTicket={handleCreateTicket}
            defaultTab={drawerTab}
            isMobile={isMobile}
          />

          {/* Slide-over Drawer: Infrastructure & RBAC (Left) */}
          <InfraDrawer
            isOpen={isInfraOpen}
            onClose={() => {
              setIsInfraOpen(false);
              setActiveNav('chat');
            }}
            currentRole={currentRole}
            onSelectRole={switchRole}
            threadId={threadId}
            isCacheBypassed={isCacheBypassed}
            onToggleCacheBypass={() => setIsCacheBypassed(!isCacheBypassed)}
            health={health}
            isLoadingHealth={isLoadingHealth}
            onRefreshHealth={fetchHealth}
            isMobile={isMobile}
          />
        </div>
      </div>
    </div>
  );
};
