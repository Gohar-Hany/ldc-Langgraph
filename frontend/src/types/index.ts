export type UserRole = 'customer' | 'support_agent' | 'senior_agent' | 'admin';

export type ClearanceLevel = 'L1' | 'L2' | 'L3' | 'ROOT';

export interface RoleInfo {
  role: UserRole;
  title: string;
  clearance: ClearanceLevel;
  badgeColor: string;
  description: string;
}

export const ROLE_DEFINITIONS: Record<UserRole, RoleInfo> = {
  customer: {
    role: 'customer',
    title: 'Customer',
    clearance: 'L1',
    badgeColor: 'var(--badge-customer)',
    description: 'General inquiry, view own tickets, knowledge search',
  },
  support_agent: {
    role: 'support_agent',
    title: 'Support Agent',
    clearance: 'L2',
    badgeColor: 'var(--badge-agent)',
    description: 'Ticket create/update, network diagnostic search',
  },
  senior_agent: {
    role: 'senior_agent',
    title: 'Senior Agent',
    clearance: 'L3',
    badgeColor: 'var(--badge-senior)',
    description: 'Full agent capabilities + HITL sensitive operation approvals',
  },
  admin: {
    role: 'admin',
    title: 'Administrator',
    clearance: 'ROOT',
    badgeColor: 'var(--badge-admin)',
    description: 'Unrestricted access, database queries & system diagnostics',
  },
};

export type PipelineStageId = 
  | 'guardrail_in' 
  | 'router_node' 
  | 'cloud_rag_tools' 
  | 'hitl_gate' 
  | 'synthesizer';

export type StageStatus = 'idle' | 'running' | 'completed' | 'interrupted' | 'error';

export interface PipelineStageInfo {
  id: PipelineStageId;
  label: string;
  sublabel: string;
  description: string;
  status: StageStatus;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  text: string;
  timestamp: string;
  intent?: string;
  confidence?: number;
  sources?: string[];
  thoughts?: string[];
  trace?: {
    step_name: string;
    status: string;
    details?: any;
  }[];
  cached?: boolean;
  cacheScore?: number | null;
  latencyMs?: number;
  isStreaming?: boolean;
  approvalRequired?: boolean;
  approvalStatus?: 'PENDING' | 'APPROVED' | 'REJECTED' | null;
  approvalDetails?: {
    action?: string;
    tool?: string;
    payload?: Record<string, any>;
    reason?: string;
    [key: string]: any;
  } | null;
  error?: string;
}

export interface TicketItem {
  id: number;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: 'network' | 'hardware' | 'software' | 'security' | 'general';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  created_by: string;
  assigned_to?: string | null;
  resolution_notes?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface DependencyStatus {
  status: 'ready' | 'fallback_mode' | 'degraded' | 'unconfigured';
  error?: string;
  mode?: string;
  provider?: string;
  type?: string;
}

export interface HealthReadyResponse {
  status: string;
  app_name: string;
  version: string;
  dependencies: {
    supabase_postgresql?: DependencyStatus;
    qdrant_vector_db?: DependencyStatus;
    llm_orchestrator?: DependencyStatus;
    tavily_external_search?: DependencyStatus;
    langgraph_checkpointer?: DependencyStatus;
    [key: string]: any;
  };
}

export interface DemoScenario {
  id: number;
  title: string;
  tag: 'RAG' | 'TICKETS' | 'EXTERNAL' | 'HITL' | 'RBAC' | 'ADMIN';
  prompt: string;
  targetRole: UserRole;
  description: string;
}
