# Enterprise Role-Based AI Support Agent

A modular, production-ready enterprise support system powered by **LangGraph**, **FastAPI**, **Role-Based Access Control (RBAC)**, and **Structured LLM Output**.

---

## 1. Project Overview & Business Scenario

This system implements an internal Enterprise IT Support Agent designed to process employee requests, determine intent, enforce strict role-based authorization, and conditionally route execution through specialized LangGraph workflows.

### Supported Roles & RBAC Matrix

| Role                    | Hierarchy Level | Permitted Operations                                                                                                    | Restricted Operations                                                   |
| :---------------------- | :-------------- | :---------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------- |
| **Customer**      | Level 1         | Knowledge Search (`knowledge_search`), View Own Tickets (`my_tickets_search`), Greetings (`greeting`)             | Ticket Modification, API Search, Sensitive Actions, Database Operations |
| **Support Agent** | Level 2         | Customer permissions + Create/Update Tickets (`ticket_create_update`) + External API Status (`external_api_search`) | Sensitive System Operations, Database Operations                        |
| **Senior Agent**  | Level 3         | Support Agent permissions + High-Privilege Sensitive Operations (`sensitive_operation`)                               | Direct Database Queries/Schema Alterations                              |
| **Admin**         | Level 4         | Unrestricted Access across all 8 intents + Direct Database Queries & Operations (`database_query_operation`)          | None                                                                    |

---

## 2. The 8 Supported Intents

1. `greeting`: General greetings, introductions, and pleasantries.
2. `knowledge_search`: Technical troubleshooting, IT policies, VPN and network setup documentation.
3. `my_tickets_search`: Checking status and history of user's own submitted tickets.
4. `ticket_create_update`: Creating new support tickets or modifying ticket status/priority.
5. `external_api_search`: Querying third-party vendor status pages and external API documentation.
6. `sensitive_operation`: High-privilege tasks (password resets, permission elevation, server reboot).
7. `database_query_operation`: Direct database schema queries, SQL queries, and maintenance (Admin only).
8. `out_of_scope`: General fallback for non-IT questions or spam.

---

## 3. LangGraph Architecture & Workflow

```text
               +-----------------------+
               |         START         |
               +-----------------------+
                           |
                           v
               +-----------------------+
               | Receive Message Node  |  --> (Validates input & initializes execution trace)
               +-----------------------+
                           |
                           v
               +-----------------------+
               | Classify Intent Node  |  --> (Structured Output via LLM or Deterministic Fallback)
               +-----------------------+
                           |
                           v
               +-----------------------+
               |   Intent Router Node  |  --> (Evaluates user JWT role vs INTENT_REQUIRED_ROLES)
               +-----------------------+
                           |
            +--------------+--------------+
            |                             |
      (Authorized)                  (Unauthorized)
            |                             |
            v                             v
+------------------------+   +------------------------+
| Specialized Response   |   | Handle Unauthorized    |
| Handler Node           |   | Node (403 Forbidden)   |
+------------------------+   +------------------------+
            |                             |
            +--------------+--------------+
                           |
                           v
               +-----------------------+
               |          END          |
               +-----------------------+
```

---

## 4. Project Structure

```text
ldc-Langgraph/
│
├── app/
│   ├── agent/                 # LangGraph workflow components
│   │   ├── edges/             # Conditional routing rules (RBAC & CRAG loops)
│   │   │   ├── routing_rules.py
│   │   │   └── rag_edges.py
│   │   ├── nodes/             # Receive, Classify, Router, RAG, and Response nodes
│   │   │   ├── receive_node.py
│   │   │   ├── classify_node.py
│   │   │   ├── router_node.py
│   │   │   ├── rag_nodes.py   # Corrective RAG (retrieve, grade, generate, rewrite)
│   │   │   └── response_nodes.py
│   │   ├── prompts/           # Prompts for classifier and grounded RAG synthesis
│   │   ├── graph.py           # Compiled StateGraph workflow with MemorySaver checkpointer
│   │   └── state.py           # AgentState TypedDict definition
│   │
│   ├── api/                   # FastAPI REST API layer
│   │   ├── middlewares/       # Request logging and unified error handlers
│   │   ├── v1/
│   │   │   ├── endpoints/     # Auth, Chat, and Ticket route handlers
│   │   │   │   ├── auth.py
│   │   │   │   ├── chat.py
│   │   │   │   └── tickets.py # Phase 3 Ticket CRUD REST API
│   │   │   └── router.py      # v1 router aggregator
│   │   └── dependencies.py    # JWT Bearer extraction and RBAC guards
│   │
│   ├── core/                  # Core infrastructure and settings
│   │   ├── config.py          # Pydantic BaseSettings (.env loader)
│   │   ├── logging.py         # Structured logging configuration
│   │   └── security.py        # Bcrypt hashing and PyJWT token utilities
│   │
│   ├── schemas/               # Pydantic contracts and domain data models
│   │   ├── auth_schema.py     # UserRole enum, UserProfile, and Token models
│   │   ├── chat_schema.py     # ChatRequest, ChatResponse, ExecutionStep
│   │   ├── intent_schema.py   # IntentType enum and IntentClassificationOutput
│   │   ├── rag_schema.py      # KnowledgeChunk, ChunkMetadata, RAGGradeOutput
│   │   └── ticket_schema.py   # TicketCreate, TicketUpdate, TicketResponse
│   │
│   ├── services/              # External cloud services
│   │   ├── llm_service.py     # OpenRouter & Aurai Studio integration
│   │   ├── openrouter_embedding.py # Cloud embeddings (text-embedding-3-small)
│   │   ├── qdrant_cloud_service.py # Qdrant Cloud vector search
│   │   ├── docling_ingestion.py    # IBM Docling layout parsing & HybridChunker
│   │   └── database_service.py     # Supabase PostgreSQL relational client
│   │
│   └── main.py                # FastAPI Application Factory
│
├── data/                      # Knowledge Base & Database Migrations
│   ├── knowledge_base/        # IT policy documents (VPN, Wi-Fi, MFA, Hardware, Software)
│   └── migrations/            # Supabase SQL schemas (001_phase3_initial_schema.sql)
│
├── tests/                     # Automated Test Suite (48 tests passing)
│   ├── conftest.py            # Pytest fixtures and test tokens for all 4 roles
│   ├── integration/           # Integration tests for Chat, RAG, and Tickets APIs
│   │   ├── test_api_chat.py
│   │   ├── test_rag_chat.py
│   │   └── test_tickets_api.py
│   ├── unit/                  # Unit tests for Classifier, RBAC, Ingestion, and Tickets
│   │   ├── test_auth.py
│   │   ├── test_intent_classifier.py
│   │   ├── test_rbac_router.py
│   │   ├── test_qdrant_service.py
│   │   ├── test_docling_ingestion.py
│   │   └── test_ticket_service.py
│   ├── live_demo.py           # End-to-end multi-turn demo script
│   └── runner.py              # Standalone test runner
│
├── docs/                      # Architecture documentation & guides
├── .env.example               # Environment variables template
├── postman_collection.json    # Complete Postman Collection (v2.1.0)
├── pytest.ini                 # Pytest path configuration
├── requirements.txt           # Production dependencies
└── README.md                  # Project documentation
```


---

## 5. Prerequisites & Installation

### Prerequisites

* Python 3.10+
* Git

### Step 1: Create and Activate Virtual Environment

#### On Linux / WSL (Recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### On Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 6. Environment Configuration

Copy the template file to create your local `.env`:

```bash
cp .env.example .env
```

### Supported Providers:

You can switch between **Aurai Studio** and **OpenRouter** in `.env`:

```env
# Application Metadata
APP_NAME="Enterprise AI Support Agent"
APP_VERSION="1.0.0"
ENVIRONMENT="development"
HOST="0.0.0.0"
PORT=8000

# Active LLM Provider: "aurai" or "openrouter"
LLM_PROVIDER="openrouter"

# Aurai Studio Configuration
AURAI_API_KEY="your_aurai_key_here"
AURAI_BASE_URL="https://api-pilot-sandbox.aurai.solutions/v1"
AURAI_MODEL="Aurai-3.0"
AURAI_TEMPERATURE=0.8
AURAI_TOP_P=0.1
AURAI_MAX_TOKENS=2048

# OpenRouter Configuration
OPENROUTER_API_KEY="sk-or-v1-your-key-here"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
OPENROUTER_MODEL="qwen/qwen-2.5-72b-instruct"

# Security & JWT Configuration
JWT_SECRET_KEY="your_secure_random_jwt_secret_key"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## 7. Running the Application

Start the development server with Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* **Interactive Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 8. Automated Testing

### Run Complete Pytest Suite (30 Tests)

```bash
pytest -v
```

### Run Standalone Test Runner

```bash
python tests/runner.py
```

### Run Live 6-Scenario Demonstration

```bash
python tests/live_demo.py
```

---

## 9. Postman Collection Guide

A complete Postman Collection is provided in [`postman_collection.json`](postman_collection.json).

### How to Import & Use:

1. Open **Postman**.
2. Click **Import** (top left).
3. Select or drag [`postman_collection.json`](postman_collection.json).
4. The collection **`Enterprise AI Support Agent - LangGraph API`** will appear with 6 organized folders:

```text
postman_collection.json
├── 00 - Health & Diagnostics
│   ├── Health Check Endpoint
│   └── API Root Welcome
│
├── 01 - Authentication (Token Generation)
│   ├── 1. Generate Customer Token     (Auto-saves customer_token & active_token)
│   ├── 2. Generate Support Agent Token (Auto-saves support_token & active_token)
│   ├── 3. Generate Senior Agent Token  (Auto-saves senior_token & active_token)
│   ├── 4. Generate Admin Token         (Auto-saves admin_token & active_token)
│   └── 5. Get Current User Profile (/me)
│
├── 02 - Customer Scenarios
│   ├── 1. Customer - Greeting (Authorized)
│   ├── 2. Customer - Knowledge Search VPN (Authorized)
│   ├── 3. Customer - Check My Tickets (Authorized)
│   ├── 4. Customer - Attempt Ticket Management (403 Expected)
│   ├── 5. Customer - Attempt Password Reset (403 Expected)
│   └── 6. Customer - Attempt SQL Query (403 Expected)
│
├── 03 - Support Agent Scenarios
│   ├── 1. Support Agent - Create Ticket (Authorized)
│   ├── 2. Support Agent - External API Search (Authorized)
│   └── 3. Support Agent - Attempt Sensitive Action (403 Expected)
│
├── 04 - Senior Agent Scenarios
│   ├── 1. Senior Agent - Password Reset (Authorized)
│   ├── 2. Senior Agent - Server Reboot (Authorized)
│   └── 3. Senior Agent - Attempt Direct SQL Query (403 Expected)
│
├── 05 - Admin Scenarios
│   ├── 1. Admin - SQL Query & Schema Inspection (Authorized)
│   └── 2. Admin - Execute Sensitive Operations (Authorized)
│
└── 06 - Edge Cases & Fallbacks
    ├── 1. Out of Scope Query (General Fallback)
    └── 2. Unauthenticated Guest Request
```

### Automatic Token Handling:

When you execute any request in `01 - Authentication`, Postman's test script automatically captures the returned JWT token and updates the collection variables (`active_token`, `customer_token`, etc.), allowing immediate execution of subsequent chat requests without manual token copying.

---

## 10. Implementation Roadmap

- [X] **Phase 1: LangGraph Foundation, Multi-Intent Classification & RBAC** (Completed)
  - 8 Supported Intents with Structured Output.
  - Role-Based Access Control matrix (Customer, Support Agent, Senior Agent, Admin).
  - JWT Authentication & FastAPI REST endpoints.
  - Complete test suite & Postman Collection.
- [X] **Phase 2: Knowledge Base & Agentic RAG Pipeline (Qdrant Cloud & Docling)** (Completed)
  - 100% Cloud Qdrant Vector database integration (`enterprise_knowledge`).
  - Document parsing with IBM Docling HybridChunker (32 section-aware chunks).
  - Cloud embeddings (`openai/text-embedding-3-small`) via OpenRouter.
  - Corrective RAG (CRAG) flow with self-correction and grounded citations.
  - Multi-turn conversation persistence (`MemorySaver`).
- [X] **Phase 3: Relational Database & Ticket Tool Integrations (Supabase PostgreSQL)** (Completed)
  - Managed Cloud PostgreSQL database integration via Supabase.
  - Production Ticket Management system (`/api/v1/tickets`) with RBAC enforcement.
  - Live database wiring for LangGraph agent nodes (`handle_my_tickets_search`, `handle_ticket_create_update`).
  - Immutable audit trail logging (`audit_logs`).
  - Comprehensive automated unit and integration test coverage (9 new tests).
- [X] **Phase 4: External APIs (Tavily Search) & Human-in-the-Loop Workflows** (Completed)
  - Real-time cloud status and external vendor monitoring powered by Tavily Search API (`tavily-python`).
  - Resilient IT status fallback engine (AWS, GitHub, Cloudflare, Zoom, Slack telemetry).
  - Production Human-in-the-Loop (HITL) approval workflow using LangGraph native `interrupt()` and `Command(resume=...)`.
  - Supervisor approval decision REST endpoints (`/api/v1/chat/approvals/{thread_id}/decide`).
  - Immutable audit logging in Supabase PostgreSQL for all sensitive approval actions.
  - Automated unit and integration test suite with 100% pass rate.
- [X] **Phase 5: Productionization, Reliability, Observability & Final Enterprise Agent** (Completed)
  - Thread-safe Metrics and Telemetry service (`/metrics`) supporting JSON and Prometheus exposition format.
  - Request Tracing and Correlation ID middleware (`X-Request-ID` and `X-Process-Time-Ms`).
  - Kubernetes-compatible health probes (`/health/live` liveness and `/health/ready` deep dependency audit).
  - Sliding-window Rate Limiting middleware (`429 Too Many Requests`) for DoS protection.
  - Production containerization with multi-stage `Dockerfile` and `docker-compose.yml`.
  - Comprehensive End-to-End multi-role test suite (`test_phase5_e2e.py`) validating the complete lifecycle.
- [X] **Phase 6: Distributed State Durability & Horizontal Scalability (PostgreSQL Checkpointer)** (Completed)
  - Enterprise PostgreSQL persistent checkpointer via official `langgraph-checkpoint-postgres` and `psycopg-pool`.
  - Seamless state durability across server crashes, restarts, and multi-pod Kubernetes horizontal scaling.
  - Persistent preservation of Human-in-the-Loop (`interrupt()`) execution states for supervisor decision resumption.
  - Resilient checkpointer factory with automated migration and graceful fallback to `MemorySaver`.
  - Complete integration test suite (`test_phase6_postgres_checkpointer.py`) with 100% pass rate.
- [X] **Phase 7: Real-Time Token & Agent Reasoning Streaming (Server-Sent Events - SSE)** (Completed)
  - Real-time streaming endpoint (`POST /api/v1/chat/stream`) with HTTP `text/event-stream`.
  - Structured event protocol: `step`, `thought`, `token`, `interrupt`, and `done`.
  - Live agent explainability broadcasting intermediate thoughts (retrieving, grading, rewriting).
  - Word-by-word streaming typing effect delivering TTFT (Time-To-First-Token) < 500ms.
  - Postman Collection updated with Folder `11 - Real-Time Streaming (Phase 7)`.
  - Full integration test suite (`test_phase7_streaming.py`) with 100% pass rate.

---

## 11. Production Docker Deployment

Deploy the entire enterprise agent stack with Docker Compose:

```bash
# 1. Build and launch container in background
docker compose up -d --build

# 2. Inspect container status and healthchecks
docker compose ps

# 3. View live streaming application logs
docker compose logs -f

# 4. Verify readiness probe
curl http://localhost:8000/health/ready

# 5. Query system telemetry metrics
curl http://localhost:8000/metrics?format=prometheus
```
