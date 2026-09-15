# LDC Enterprise AI Console — Complete UI Brief & API Documentation

> **For:** Frontend Developer / UI Engineer  
> **Version:** 2.5  
> **Date:** September 2026  
> **Prepared by:** Link Datacenter Engineering Team

---

## Table of Contents

1. [Project Overview & Purpose](#1-project-overview--purpose)
2. [Brand Identity & Design System](#2-brand-identity--design-system)
3. [Application Architecture](#3-application-architecture)
4. [User Roles & Personas (RBAC)](#4-user-roles--personas-rbac)
5. [Core UI Screens & Layout](#5-core-ui-screens--layout)
6. [API Reference — Complete Endpoints](#6-api-reference--complete-endpoints)
   - [Base URL & Authentication](#base-url--authentication)
   - [Auth API](#auth-api)
   - [Chat API (Main Agent)](#chat-api-main-agent)
   - [Streaming API (SSE)](#streaming-api-sse)
   - [HITL Approval API](#hitl-approval-api)
   - [Tickets API](#tickets-api)
   - [Health & Metrics API](#health--metrics-api)
7. [SSE Event Types (Streaming)](#7-sse-event-types-streaming)
8. [LangGraph Pipeline — Visual Stages](#8-langgraph-pipeline--visual-stages)
9. [Human-in-the-Loop (HITL) Workflow](#9-human-in-the-loop-hitl-workflow)
10. [Intent Classification System](#10-intent-classification-system)
11. [Key UI Components Needed](#11-key-ui-components-needed)
12. [UX Scenarios to Test](#12-ux-scenarios-to-test)

---

## 1. Project Overview & Purpose

### What is this?

The **LDC Enterprise AI Console** is the operations dashboard and conversational interface for **Link Datacenter**'s autonomous AI support agent. It is a **professional enterprise web application** used by:

- **Customers** to get instant answers about services, SLAs, data centers, connectivity
- **Support Agents** to handle tickets, escalate issues, and search the knowledge base
- **Senior Agents & Admins** to approve sensitive operations (refunds, billing mutations)

### What does the AI Agent do?

The backend is a **LangGraph-powered agentic pipeline** (FastAPI + Python) that:

1. Receives a natural language message
2. Redacts PII (Presidio guardrails)
3. Checks semantic vector cache (Qdrant, <40ms if hit)
4. Classifies intent (8 categories) with LLM
5. Enforces RBAC (Role-Based Access Control) per intent
6. Routes to the appropriate handler:
   - **RAG** (Qdrant hybrid search over enterprise knowledge base)
   - **Tickets** (Supabase PostgreSQL)
   - **External search** (Tavily web search)
   - **HITL gate** (pauses execution for supervisor approval)
   - **Database queries** (admin diagnostics)
7. Streams response tokens + agent reasoning to the frontend via SSE

### Why do we need a UI?

The backend is fully functional and production-ready. The UI is the **human interface layer** that:
- Lets users interact naturally via chat
- Shows the **LangGraph pipeline progress** in real-time (which nodes are active)
- Displays **agent reasoning** (thought chain) transparently
- Shows **citation sources** from the knowledge base
- Triggers and displays **HITL approval banners** when sensitive operations are paused
- Allows supervisors to **approve/reject** operations with audit notes
- Displays **system health** of all backend services (Supabase, Qdrant, LLM)
- Supports **RBAC persona switching** for testing different access levels

---

## 2. Brand Identity & Design System

### Company

**Link Datacenter** — Egypt & UAE's premier Tier-III Cloud Facility

**Tagline:** *The Region's Cloud Powerhouse*

**Logo:** Available as `/ldc_logo.webp` (served from public folder of Next.js)

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--ldc-green` | `#00a36c` | Primary brand, CTAs, active states |
| `--ldc-green-dark` | `#007a50` | Hover states, dark text on green |
| `--ldc-green-light` | `#e8f7f1` | Backgrounds, badges, highlights |
| `--ldc-green-mid` | `#b3e6d0` | Borders, dividers |
| `--bg-app` | `#f0f4f8` | App background (light grey) |
| `--bg-card` | `#ffffff` | Cards, panels |
| `--border` | `#e2e8f0` | Default borders |
| `--text-primary` | `#1a2332` | Main text |
| `--text-secondary` | `#475569` | Secondary text |
| `--text-muted` | `#94a3b8` | Labels, captions |

**Semantic Colors:**
- Success/Green: `#00a36c`
- Warning/Amber: `#f59e0b`
- Error/Red: `#ef4444`
- Info/Blue: `#3b82f6`

### Typography

- **Primary Font:** Inter (Google Fonts) — weights 400, 500, 600, 700, 800
- **Monospace Font:** JetBrains Mono — for code, thread IDs, JSON payloads

### Design Language

> **Clean, Professional, Enterprise Light Theme** — similar to modern SaaS dashboards (Linear, Vercel, Kayanova Studio)

- White card surfaces on light grey background
- Subtle shadows (`box-shadow: 0 1px 3px rgba(0,0,0,0.05)`)
- Smooth border radius (`8px` for inputs/buttons, `12px` for cards)
- Green accent for all interactive and active elements
- **No dark mode** — this is a professional enterprise tool

---

## 3. Application Architecture

```
Frontend (Next.js 15+ / Vite)
    │
    ├── Auth: JWT Bearer Token in Authorization header
    │         (Token obtained from POST /api/v1/auth/token)
    │
    ├── Main API: POST /api/v1/chat/stream  ← SSE streaming (PRIMARY)
    │             POST /api/v1/chat          ← Non-streaming (fallback)
    │
    ├── HITL: POST /api/v1/chat/approvals/{thread_id}/decide
    │         GET  /api/v1/chat/approvals/{thread_id}/status
    │
    ├── Tickets: GET/POST /api/v1/tickets
    │
    └── Health: GET /health/ready
```

**Backend runs at:** `http://localhost:8001` (dev) or your production URL

**CORS Allowed Origins:** `http://localhost:3000`, `http://localhost:3001`, `http://localhost:8080`

---

## 4. User Roles & Personas (RBAC)

The system has 4 roles with increasing clearance levels:

| Role | Code | Clearance Level | Description |
|------|------|-----------------|-------------|
| Customer | `customer` | L1 | End users — can ask questions, view own tickets |
| Support Agent | `support_agent` | L2 | Create/update tickets, external search |
| Senior Agent | `senior_agent` | L3 | Approve HITL sensitive operations |
| Administrator | `admin` | ROOT | Full access including DB queries |

### Intent × Role Permission Matrix

| Intent | Customer | Support Agent | Senior Agent | Admin |
|--------|----------|---------------|--------------|-------|
| `greeting` | ✅ | ✅ | ✅ | ✅ |
| `knowledge_search` | ✅ | ✅ | ✅ | ✅ |
| `my_tickets_search` | ✅ | ✅ | ✅ | ✅ |
| `ticket_create_update` | ❌ | ✅ | ✅ | ✅ |
| `external_api_search` | ❌ | ✅ | ✅ | ✅ |
| `sensitive_operation` | ❌ | ❌ | ✅ (requires HITL) | ✅ (requires HITL) |
| `database_query_operation` | ❌ | ❌ | ❌ | ✅ |
| `out_of_scope` | ✅ | ✅ | ✅ | ✅ |

---

## 5. Core UI Screens & Layout

### Main Layout Structure

```
┌──────────────────────────────────────────────────────┐
│  SIDEBAR (260px)    │  HEADER (60px height, sticky)  │
│                     ├────────────────────────────────│
│  - LDC Logo + Brand │  PIPELINE STEPPER (44px strip) │
│  - Access Level     ├────────────────────────────────│
│    (Persona Switch) │                                │
│  - System Health    │  CHAT / MAIN CONTENT AREA      │
│  - Session Thread   │  (flex-1, scrollable)          │
│                     │                                │
│                     │  Welcome screen OR messages    │
│                     │                                │
│                     ├────────────────────────────────│
│                     │  INPUT BAR (fixed at bottom)   │
└──────────────────────────────────────────────────────┘
```

### Screen States

1. **Empty/Welcome State** — Hero banner + Quick Scenario cards (no messages yet)
2. **Chat Active** — Message bubbles (user right, agent left) with streaming cursor
3. **HITL Interrupt** — Alert banner between messages requiring supervisor decision
4. **Streaming** — Agent bubble with animated cursor, pipeline stepper animating
5. **Error State** — Error bubble in red

---

## 6. API Reference — Complete Endpoints

### Base URL & Authentication

```
Base URL: http://localhost:8001
API Prefix: /api/v1
```

**Authentication:** All endpoints (except `/health/*` and `/`) require:
```http
Authorization: Bearer <JWT_TOKEN>
```

**How to get a JWT token:**
```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "user_id": "user_01",
  "role": "customer"
}
```

---

### Auth API

#### `POST /api/v1/auth/token`
Generate a JWT token for a specific role (used for testing/demo).

**Request Body:**
```json
{
  "user_id": "string",   // e.g., "user_01", "agent_sara"
  "role": "customer"     // "customer" | "support_agent" | "senior_agent" | "admin"
}
```

**Response `200 OK`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "customer"
}
```

---

#### `GET /api/v1/auth/me`
Get current user profile from JWT.

**Response `200 OK`:**
```json
{
  "id": "user_01",
  "email": "user_01@company.com",
  "full_name": "User_01",
  "role": "customer",
  "is_active": true
}
```

---

### Chat API (Main Agent)

#### `POST /api/v1/chat`
Send a message and receive a **non-streaming** complete response.

**Request Headers:**
```http
Authorization: Bearer <token>
Content-Type: application/json
X-Bypass-Cache: true   # Optional — bypass semantic cache, force live LLM
```

**Request Body:**
```json
{
  "message": "What are your SLA guarantees for Tier-III colocation?",
  "thread_id": "thread_ldc_abc123xyz",    // LangGraph conversation ID (persistent)
  "conversation_id": "thread_ldc_abc123xyz"  // Synonym for thread_id
}
```

**Response `200 OK` — Normal completion:**
```json
{
  "response": "Our Tier-III colocation guarantees 99.982% uptime SLA...",
  "intent": "knowledge_search",
  "confidence": 0.97,
  "user_role": "customer",
  "is_authorized": true,
  "conversation_id": "thread_ldc_abc123xyz",
  "thread_id": "thread_ldc_abc123xyz",
  "sources": [
    "LDC SLA Policy v3.2 — Section 4.1",
    "Colocation Service Agreement — Uptime Guarantees"
  ],
  "execution_trace": [
    {"step_name": "receive_message", "status": "success", "details": null},
    {"step_name": "semantic_cache_check", "status": "success", "details": null},
    {"step_name": "classify_intent", "status": "success", "details": null},
    {"step_name": "router_node", "status": "success", "details": null},
    {"step_name": "rag_retrieve", "status": "success", "details": null},
    {"step_name": "rag_generate", "status": "success", "details": null}
  ],
  "external_results": null,
  "approval_required": false,
  "approval_status": null,
  "approval_details": null,
  "cached": false,
  "cache_score": null
}
```

**Response `200 OK` — HITL Interrupt (sensitive operation paused):**
```json
{
  "response": "[APPROVAL REQUIRED - SENSITIVE OPERATION]\nThis high-privilege action requires supervisor or administrative approval.\n- Thread ID: thread_ldc_abc123xyz\n- Operation: 'Process refund of $450 for customer Ahmed'\n- Status: PENDING_SUPERVISOR_APPROVAL\nA supervisor can approve or reject via POST /api/v1/chat/approvals/thread_ldc_abc123xyz/decide",
  "intent": "sensitive_operation",
  "confidence": 0.99,
  "user_role": "senior_agent",
  "is_authorized": true,
  "conversation_id": "thread_ldc_abc123xyz",
  "thread_id": "thread_ldc_abc123xyz",
  "approval_required": true,
  "approval_status": "PENDING",
  "approval_details": {
    "action": "process_refund",
    "tool": "financial_mutation_tool",
    "payload": {"amount": 450, "customer_id": "C-4892", "reason": "SLA breach"},
    "reason": "Refund exceeds $200 threshold requiring supervisor sign-off"
  },
  "sources": [],
  "execution_trace": [...],
  "cached": false,
  "cache_score": null
}
```

**Response `200 OK` — Cache Hit (very fast, <40ms):**
```json
{
  "response": "Our Tier-III colocation guarantees 99.982% uptime...",
  "intent": "knowledge_search",
  "confidence": 0.97,
  "cached": true,
  "cache_score": 0.9847,
  ...
}
```

---

### Streaming API (SSE)

#### `POST /api/v1/chat/stream`
Send a message and receive **real-time streaming** via Server-Sent Events.

**This is the PRIMARY API the UI should use.**

**Request Headers:**
```http
Authorization: Bearer <token>
Content-Type: application/json
X-Bypass-Cache: true   # Optional
```

**Request Body:** Same as `/chat`
```json
{
  "message": "What are the power specifications for your Cairo DC?",
  "thread_id": "thread_ldc_abc123xyz"
}
```

**Response:** `text/event-stream` (SSE)

See **Section 7** for all SSE event types.

**Frontend JavaScript (EventSource / fetch):**
```javascript
const response = await fetch('http://localhost:8001/api/v1/chat/stream', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ message, thread_id }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('event: ')) {
      currentEvent = line.slice(7).trim();
    } else if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      handleEvent(currentEvent, data);
    }
  }
}
```

---

### HITL Approval API

#### `POST /api/v1/chat/approvals/{thread_id}/decide`
**Supervisor only** — Approve or reject a paused sensitive operation.

> ⚠️ Requires `senior_agent` or `admin` role. Returns `403 Forbidden` otherwise.

**Path Parameter:** `thread_id` — the LangGraph thread that is paused

**Request Headers:**
```http
Authorization: Bearer <senior_agent_or_admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "approved": true,
  "reviewer_notes": "Refund approved — SLA breach confirmed by monitoring team"
}
```

**Response `200 OK` — After approval, agent resumes and returns final answer:**
```json
{
  "response": "Refund of $450 has been successfully processed for customer C-4892. Reference: REF-20260912-001.",
  "intent": "sensitive_operation",
  "confidence": 1.0,
  "user_role": "senior_agent",
  "is_authorized": true,
  "thread_id": "thread_ldc_abc123xyz",
  "approval_required": false,
  "approval_status": "APPROVED",
  "approval_details": {
    "resumed_by": "agent_sara",
    "approved": true
  },
  "sources": [],
  "execution_trace": [...],
  "cached": false
}
```

**Response `403 Forbidden`:**
```json
{
  "detail": "Forbidden: Only Senior Agents or Administrators can review and decide sensitive operations."
}
```

**Response `400 Bad Request` (no pending approval):**
```json
{
  "detail": "No pending approval found for thread 'thread_ldc_abc123xyz'. The thread is not currently paused."
}
```

---

#### `GET /api/v1/chat/approvals/{thread_id}/status`
Poll whether a thread is currently awaiting approval.

**Response `200 OK`:**
```json
{
  "thread_id": "thread_ldc_abc123xyz",
  "is_pending_approval": true,
  "next_nodes": ["handle_sensitive_operation"],
  "interrupts": [
    {
      "action": "process_refund",
      "tool": "financial_mutation_tool",
      "payload": {"amount": 450, "customer_id": "C-4892"},
      "reason": "Refund exceeds $200 threshold"
    }
  ]
}
```

---

### Tickets API

#### `POST /api/v1/tickets`
Create a new support ticket.

**Accessible to:** All authenticated roles

**Request Body:**
```json
{
  "title": "Server rack cooling issue in Cairo-DC-A3",
  "description": "Temperature sensors showing 38°C in rack A3-12. Threshold is 35°C.",
  "priority": "high",       // "low" | "medium" | "high" | "critical"
  "category": "hardware"    // "network" | "hardware" | "software" | "security" | "general"
}
```

**Response `201 Created`:**
```json
{
  "id": 1042,
  "title": "Server rack cooling issue in Cairo-DC-A3",
  "description": "Temperature sensors showing 38°C in rack A3-12...",
  "status": "open",
  "priority": "high",
  "category": "hardware",
  "created_by": "user_01",
  "assigned_to": null,
  "resolution_notes": null,
  "created_at": "2026-09-12T02:15:30Z",
  "updated_at": "2026-09-12T02:15:30Z"
}
```

---

#### `GET /api/v1/tickets/my`
Get all tickets created by the currently authenticated user.

**Accessible to:** All roles (customer isolation enforced)

**Response `200 OK`:**
```json
[
  {
    "id": 1042,
    "title": "Server rack cooling issue",
    "status": "open",
    "priority": "high",
    "category": "hardware",
    "created_by": "user_01",
    "created_at": "2026-09-12T02:15:30Z"
  }
]
```

---

#### `GET /api/v1/tickets`
List all tickets with optional filtering.

> ⚠️ Customer role gets `403 Forbidden`. Agents and Admins only.

**Query Parameters:**
```
?status=open             # "open" | "in_progress" | "resolved" | "closed"
?priority=high           # "low" | "medium" | "high" | "critical"
?category=hardware       # "network" | "hardware" | "software" | "security" | "general"
?created_by=user_01      # Filter by user ID
?limit=20                # 1-100, default 20
?offset=0                # Pagination offset
```

**Response `200 OK`:** Array of `TicketResponse` objects (same structure as above)

---

#### `PATCH /api/v1/tickets/{ticket_id}`
Update ticket status, priority, assignee, or resolution notes.

> ⚠️ Customer role gets `403 Forbidden`. Agents and Admins only.

**Path Parameter:** `ticket_id` (integer)

**Request Body** (all fields optional):
```json
{
  "status": "in_progress",
  "priority": "critical",
  "category": "security",
  "assigned_to": "agent_sara",
  "resolution_notes": "Escalated to data center ops team for physical inspection."
}
```

**Response `200 OK`:** Updated `TicketResponse` object

**Response `404 Not Found`:**
```json
{
  "detail": "Ticket #9999 not found."
}
```

---

### Health & Metrics API

#### `GET /health`
Basic application health check.

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "app_name": "Enterprise AI Support Agent",
  "version": "1.0.0",
  "environment": "development"
}
```

---

#### `GET /health/ready`
Full readiness check — verifies all external dependencies.

**Response `200 OK`:**
```json
{
  "status": "ready",
  "app_name": "Enterprise AI Support Agent",
  "version": "1.0.0",
  "dependencies": {
    "supabase_postgresql": {"status": "ready"},
    "qdrant_vector_db": {"status": "ready"},
    "llm_orchestrator": {"status": "ready", "provider": "openrouter"},
    "tavily_external_search": {"status": "fallback_mode", "mode": "resilient_fallback"},
    "langgraph_checkpointer": {"status": "ready", "type": "PostgresSaver"}
  }
}
```

**Status values per dependency:** `"ready"` | `"fallback_mode"` | `"degraded"` | `"unconfigured"`

> **UI note:** Poll this every 25 seconds to show live system health in the sidebar.

---

#### `GET /metrics`
Telemetry metrics.

**Query Parameter:** `?format=prometheus` for Prometheus format, default is JSON.

---

## 7. SSE Event Types (Streaming)

The `/api/v1/chat/stream` endpoint emits the following SSE event types in order:

### Event: `step`
Fired when a LangGraph node starts/completes. Shows which pipeline stage is active.

```
event: step
data: {"step": "start", "status": "connected", "thread_id": "thread_ldc_abc123"}
```

```
event: step
data: {
  "node": "semantic_cache_check",
  "status": "completed",
  "thought": "Checking vector semantic cache for previous answers...",
  "intent": null,
  "is_authorized": true
}
```

**Possible `node` values:**
| Node Name | Pipeline Stage | Thought Message |
|-----------|----------------|-----------------|
| `receive_message` | Guardrail In | "Message received and validated." |
| `semantic_cache_check` | Semantic Router | "Checking vector semantic cache..." |
| `classify_intent` | Semantic Router | "Classified intent as '{intent}'." |
| `router_node` | Semantic Router | "Verifying role-based permissions (RBAC)..." |
| `rag_retrieve` | RAG / Cloud Tools | "Searching enterprise knowledge base..." |
| `rag_grade` | RAG / Cloud Tools | "Grading relevance of retrieved documents..." |
| `rag_rewrite` | RAG / Cloud Tools | "Refining search query..." |
| `rag_generate` | RAG / Cloud Tools | "Formulating grounded answer with citations..." |
| `handle_my_tickets_search` | RAG / Cloud Tools | "Fetching user support tickets from database..." |
| `handle_ticket_create_update` | RAG / Cloud Tools | "Executing ticket creation in database..." |
| `handle_external_api_search` | RAG / Cloud Tools | "Querying external search and status API..." |
| `handle_sensitive_operation` | HITL Gate | "Evaluating sensitive operation permissions..." |
| `handle_database_query` | HITL Gate | "Executing diagnostic database query..." |
| `handle_unauthorized` | Synthesizer | "Access denied: User lacks required role permissions." |
| `handle_fallback` | Synthesizer | "Synthesizing fallback response." |
| `handle_greeting` | Synthesizer | "Synthesizing welcoming greeting..." |

---

### Event: `thought`
Agent reasoning step — display in a collapsible "Agent Reasoning" accordion.

```
event: thought
data: {"thought": "Classified intent as 'knowledge_search'."}
```

---

### Event: `token`
One word/chunk of the final response — append to agent message bubble.

```
event: token
data: {"token": "Our "}

event: token
data: {"token": "Tier-III "}

event: token
data: {"token": "colocation "}
```

---

### Event: `interrupt`
**HITL triggered** — agent execution paused. Show approval banner immediately.

```
event: interrupt
data: {
  "approval_required": true,
  "thread_id": "thread_ldc_abc123",
  "status": "PENDING_SUPERVISOR_APPROVAL",
  "details": {
    "action": "process_refund",
    "tool": "financial_mutation_tool",
    "payload": {"amount": 450, "customer_id": "C-4892"},
    "reason": "Refund exceeds $200 supervisor threshold"
  }
}
```

---

### Event: `done`
Stream complete. Contains full final data.

```
event: done
data: {
  "final_response": "Our Tier-III colocation guarantees 99.982% uptime...",
  "intent": "knowledge_search",
  "is_authorized": true,
  "thread_id": "thread_ldc_abc123",
  "sources": ["LDC SLA Policy v3.2", "Colocation Agreement"],
  "external_results": null,
  "approval_required": false,
  "approval_status": null,
  "cached": false,
  "cache_score": null
}
```

**`done` event when HITL triggered:**
```
event: done
data: {
  "final_response": "Approval required for sensitive operation.",
  "approval_required": true,
  "thread_id": "thread_ldc_abc123",
  "approval_status": "PENDING",
  "cached": false
}
```

---

### Event: `error`
Something went wrong. Show error state in UI.

```
event: error
data: {"error": "LLM timeout after 15 seconds"}
```

---

## 8. LangGraph Pipeline — Visual Stages

The agent pipeline has **5 visual stages** to display in the UI as a horizontal stepper/breadcrumb:

| Stage # | Stage ID | Label | Description | Maps to Nodes |
|---------|----------|-------|-------------|---------------|
| 1 | `guardrail_in` | Guardrail In | Presidio PII Redaction & Prompt Shield | `receive_message` |
| 2 | `router_node` | Semantic Router | Vector Cache Lookup & RBAC Intent Classifier | `semantic_cache_check`, `classify_intent`, `router_node` |
| 3 | `cloud_rag_tools` | RAG / Cloud Tools | Qdrant Hybrid Knowledge & Support Database | `rag_*`, `handle_my_tickets_search`, `handle_ticket_create_update`, `handle_external_api_search`, `handle_database_query` |
| 4 | `hitl_gate` | HITL Approval Gate | Supervisor Authorization for Sensitive Actions | `handle_sensitive_operation`, `__interrupt__` |
| 5 | `synthesizer` | LDC Synthesizer | Context Grounding, Guardrails Out & Streaming | `rag_generate`, `handle_greeting`, `handle_fallback`, `handle_unauthorized` |

**Node → Stage Mapping Logic:**
```javascript
function mapNodeToStage(nodeName) {
  if (nodeName.includes('receive_message')) return 'guardrail_in';
  if (nodeName.includes('cache') || nodeName.includes('classify') || nodeName.includes('router')) return 'router_node';
  if (nodeName.includes('rag') || nodeName.includes('ticket') || nodeName.includes('search') || nodeName.includes('database')) return 'cloud_rag_tools';
  if (nodeName.includes('sensitive') || nodeName.includes('interrupt')) return 'hitl_gate';
  return 'synthesizer';
}
```

**Stage Visual States:**
- `idle` — Default grey
- `running` — Green with pulse animation
- `completed` — Green with checkmark ✓
- `interrupted` — Amber with warning ⚠
- `error` — Red with ✕

---

## 9. Human-in-the-Loop (HITL) Workflow

This is the most critical and complex UI flow:

### Step-by-Step Flow

```
1. User (Senior Agent) sends message:
   "Process a $450 refund for customer Ahmed — SLA breach"

2. Backend classifies as `sensitive_operation`

3. LangGraph hits interrupt node → pauses execution

4. SSE stream emits `event: interrupt` with details

5. UI shows HITL Approval Banner with:
   - ⚠️ "HITL APPROVAL REQUIRED" header
   - Action: "process_refund"
   - Reason: "Refund exceeds $200 threshold"
   - Payload: {"amount": 450, "customer_id": "C-4892"}
   - Text input for supervisor notes
   - [Reject & Cancel] button (red)
   - [Approve & Resume Workflow] button (green, primary)

6. If current user is NOT senior_agent or admin:
   → Show lock icon: "Your role (L1) cannot approve sensitive ops"
   → Show "Switch to Senior Agent" CTA button

7. Supervisor clicks [Approve & Resume]:
   Frontend calls:
   POST /api/v1/chat/approvals/{thread_id}/decide
   Body: {"approved": true, "reviewer_notes": "SLA breach confirmed"}

8. Backend resumes LangGraph, executes the operation

9. API returns final ChatResponse with:
   approval_status: "APPROVED"
   response: "Refund of $450 processed. Reference REF-20260912-001"

10. UI shows system notice message:
    "[SUPERVISOR DECISION]: Operation APPROVED by Sara Ahmed (SENIOR_AGENT)"
    Then shows final agent response
```

---

## 10. Intent Classification System

The backend classifies every message into one of **8 intents**:

| Intent | Code | Description | Example Query |
|--------|------|-------------|---------------|
| Greeting | `greeting` | Salutation or general inquiry | "Hello, how can you help me?" |
| Knowledge Search | `knowledge_search` | Technical/service questions (RAG) | "What SLA does Tier-III colocation offer?" |
| My Tickets | `my_tickets_search` | User's own support tickets | "Show me my open tickets" |
| Ticket Create/Update | `ticket_create_update` | Create or modify tickets | "Create a ticket for network outage in rack B2" |
| External API Search | `external_api_search` | Real-time external data | "What's the current BGP routing status?" |
| Sensitive Operation | `sensitive_operation` | Financial/privileged actions | "Process refund of $450 for customer Ahmed" |
| Database Query | `database_query_operation` | Admin raw DB diagnostics | "Show all tickets from last 24h across all customers" |
| Out of Scope | `out_of_scope` | Irrelevant request | "What's the weather today?" |

---

## 11. Key UI Components Needed

### Required Components

```
Layout/
├── Sidebar.tsx
│   ├── Logo + Brand (LDC logo + "LINK DATACENTER" + "AI Agent Console")
│   ├── Collapse toggle (arrow button in header)
│   ├── Persona/Role Switcher (RBAC clearance level selector)
│   ├── System Health panel (live status from /health/ready)
│   └── Session Thread ID (with copy button)
│
├── Header.tsx
│   ├── Page title: "AI Agent Console"
│   ├── Backend health indicator (green ping dot)
│   ├── Cache mode toggle (Active / Bypassed)
│   ├── Active persona chip (clearance level + name)
│   └── New Session button

Graph/
└── PipelineStepper.tsx
    ├── 5 horizontal step nodes
    ├── Connector arrows between nodes
    ├── Active node pulse animation
    └── Streaming badge

Chat/
├── ChatView.tsx
│   ├── Welcome state (hero banner + scenario cards)
│   ├── Message list (scrollable)
│   ├── HITL banner (rendered inline between messages)
│   └── Input bar (textarea + send button)
│
├── MessageItem.tsx
│   ├── User bubble (right-aligned, green background)
│   ├── Agent bubble (left-aligned, white card with green left border)
│   ├── System notice (centered, green tinted)
│   ├── Reasoning accordion (collapsible "Agent Reasoning N steps")
│   ├── Streaming cursor (animated)
│   ├── Cache/Live badge
│   ├── Latency display (e.g. "1.2s latency")
│   ├── Citation sources grid
│   └── Copy button
│
└── HitlBanner.tsx
    ├── Amber gradient warning banner
    ├── Operation details card
    ├── Payload JSON viewer
    ├── Notes input (for authorized users)
    ├── Approve / Reject buttons
    └── Unauthorized state (lock + "Switch Role" CTA)

Common/
└── MarkdownRenderer.tsx
    └── Renders agent responses as rich markdown
        (headings, bullets, code blocks, tables, blockquotes)
```

---

## 12. UX Scenarios to Test

These are the 8 clickable demo scenarios to put on the welcome screen:

| # | Title | Tag | Prompt | Target Role |
|---|-------|-----|--------|-------------|
| 1 | Cairo DC — Colocation & Power SLA | `RAG` | "What are the power redundancy and uptime SLA specifications for Link Datacenter's Cairo facility?" | `customer` |
| 2 | My Support Tickets | `TICKETS` | "Show me all my open support tickets and their current status" | `support_agent` |
| 3 | BGP Route & Connectivity Status | `EXTERNAL` | "What is the current BGP routing status and any connectivity issues for our dedicated link?" | `support_agent` |
| 4 | HITL Refund Approval Flow | `HITL` | "Process a full refund of $450 for customer account C-4892 due to confirmed SLA breach in August" | `senior_agent` |
| 5 | Role-Based Access Test | `RBAC` | "Create a new ticket for a network outage in rack B-12 Cairo DC — priority critical" | `customer` |
| 6 | Create Ticket (Agent) | `TICKETS` | "Create an urgent ticket for server overheating in rack C-7, priority critical, hardware category" | `support_agent` |
| 7 | Knowledge Search | `RAG` | "Explain the difference between colocation and managed hosting at Link Datacenter" | `customer` |
| 8 | Admin DB Query | `ADMIN` | "Show me a diagnostic summary of all tickets created in the last 24 hours across all customers" | `admin` |

---

## Important Notes for the Developer

### 1. Thread ID Management
- Generate a unique `thread_id` per session: `thread_ldc_${Date.now().toString(36)}_${random}`
- Pass the same `thread_id` for every message in a conversation — LangGraph uses it for state persistence
- "New Session" button should generate a new `thread_id` and clear messages

### 2. Token Management
- For demo/dev: Use `POST /api/v1/auth/token` to get tokens per role
- Store token in memory (not localStorage) for security
- When switching persona, re-fetch a token for that role

### 3. Semantic Cache
- When `cached: true` in response → show green "Vector Cache (~35ms)" badge
- When `cached: false` → show blue "Live Inference" badge
- `X-Bypass-Cache: true` header forces live LLM (bypass toggle in header)

### 4. HITL Requirement
- When `event: interrupt` received → immediately show the HITL banner
- The thread is **paused** until `POST /approvals/{thread_id}/decide` is called
- Only `senior_agent` or `admin` tokens can call the approve/reject endpoint
- If current role is insufficient → show the role elevation CTA

### 5. Error Handling
- `401` → Token expired, re-fetch token
- `403` → Show "Access Restricted" message with role elevation option
- `429` → Rate limit hit (60 req/min per IP) → show retry message
- `500` → Internal error → show error bubble

### 6. Health Polling
- Poll `GET /health/ready` every 25 seconds
- Map dependency statuses to colored indicators in sidebar
- `"ready"` → green, `"fallback_mode"` → amber, `"degraded"` → red

---

*End of LDC Enterprise AI Console UI Brief*

> For questions: Reach out to the LDC Engineering team.  
> Backend docs also available at: `http://localhost:8001/docs` (Swagger UI)
