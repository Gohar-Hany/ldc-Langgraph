import { HealthReadyResponse, TicketItem, UserRole } from '../types';

// Direct backend URL with CORS (whitelisted http://localhost:3000, 3001)
const BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8001';

class ApiService {
  private activeToken: string | null = null;
  private activeRole: UserRole = 'customer';

  setToken(token: string, role: UserRole) {
    this.activeToken = token;
    this.activeRole = role;
  }

  getToken(): string | null {
    return this.activeToken;
  }

  getRole(): UserRole {
    return this.activeRole;
  }

  async fetchToken(role: UserRole, userId?: string): Promise<string> {
    const id = userId || (role === 'customer' ? 'user_01' : role === 'admin' ? 'admin_01' : 'agent_sara');
    const response = await fetch(`${BASE_URL}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: id, role }),
    });

    if (!response.ok) {
      throw new Error(`Failed to acquire token for role ${role}: ${response.statusText}`);
    }

    const data = await response.json();
    this.setToken(data.access_token, role);
    return data.access_token;
  }

  async getHealthReady(): Promise<HealthReadyResponse> {
    const response = await fetch(`${BASE_URL}/health/ready`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json();
  }

  async streamChat({
    message,
    threadId,
    bypassCache = false,
    onStep,
    onThought,
    onToken,
    onInterrupt,
    onDone,
    onError,
  }: {
    message: string;
    threadId: string;
    bypassCache?: boolean;
    onStep?: (data: any) => void;
    onThought?: (thought: string) => void;
    onToken?: (token: string) => void;
    onInterrupt?: (data: any) => void;
    onDone?: (data: any) => void;
    onError?: (err: string) => void;
  }): Promise<void> {
    const token = this.activeToken;
    if (!token) {
      throw new Error('Authentication required: Token not initialized.');
    }

    const headers: Record<string, string> = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };

    if (bypassCache) {
      headers['X-Bypass-Cache'] = 'true';
    }

    const response = await fetch(`${BASE_URL}/api/v1/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message,
        thread_id: threadId,
        conversation_id: threadId,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      let parsedMsg = errText;
      try {
        const json = JSON.parse(errText);
        parsedMsg = json.detail || json.error?.message || errText;
      } catch {}
      onError?.(parsedMsg);
      throw new Error(parsedMsg);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('ReadableStream not supported.');
    }

    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let currentEvent = 'message';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = 'message';
          continue;
        }

        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim();
        } else if (trimmed.startsWith('data:')) {
          const rawData = trimmed.slice(5).trim();
          try {
            const data = JSON.parse(rawData);
            switch (currentEvent) {
              case 'step':
                onStep?.(data);
                break;
              case 'thought':
                onThought?.(data.thought);
                break;
              case 'token':
                onToken?.(data.token);
                break;
              case 'interrupt':
                onInterrupt?.(data);
                break;
              case 'done':
                onDone?.(data);
                break;
              case 'error':
                onError?.(data.error || 'Pipeline execution failed');
                break;
              default:
                break;
            }
          } catch (e) {
            console.warn('Failed to parse SSE payload:', rawData, e);
          }
        }
      }
    }
  }

  async sendChatFallback({
    message,
    threadId,
    bypassCache = false,
  }: {
    message: string;
    threadId: string;
    bypassCache?: boolean;
  }) {
    const token = this.activeToken;
    const headers: Record<string, string> = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
    if (bypassCache) headers['X-Bypass-Cache'] = 'true';

    const res = await fetch(`${BASE_URL}/api/v1/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message,
        thread_id: threadId,
        conversation_id: threadId,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Chat request failed');
    }
    return res.json();
  }

  async decideApproval(threadId: string, approved: boolean, reviewerNotes: string) {
    const token = this.activeToken;
    const res = await fetch(`${BASE_URL}/api/v1/chat/approvals/${encodeURIComponent(threadId)}/decide`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        approved,
        reviewer_notes: reviewerNotes,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Approval decision rejected');
    }
    return res.json();
  }

  async getApprovalStatus(threadId: string) {
    const token = this.activeToken;
    const res = await fetch(`${BASE_URL}/api/v1/chat/approvals/${encodeURIComponent(threadId)}/status`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!res.ok) return null;
    return res.json();
  }

  async getTickets(isAgentOrAdmin: boolean): Promise<TicketItem[]> {
    const token = this.activeToken;
    const endpoint = isAgentOrAdmin ? '/api/v1/tickets' : '/api/v1/tickets/my';
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch tickets: ${res.statusText}`);
    }
    return res.json();
  }

  async createTicket(payload: {
    title: string;
    description: string;
    priority: string;
    category: string;
  }): Promise<TicketItem> {
    const token = this.activeToken;
    const res = await fetch(`${BASE_URL}/api/v1/tickets`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to create ticket');
    }
    return res.json();
  }

  async updateTicket(ticketId: number, payload: Partial<TicketItem>): Promise<TicketItem> {
    const token = this.activeToken;
    const res = await fetch(`${BASE_URL}/api/v1/tickets/${ticketId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to update ticket');
    }
    return res.json();
  }
}

export const apiService = new ApiService();
