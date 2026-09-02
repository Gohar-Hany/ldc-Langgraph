# Enterprise Role-Based AI Support Agent (LangGraph & FastAPI)

A modular, production-ready enterprise support system built with **LangGraph**, **FastAPI**, and **Role-Based Access Control (RBAC)**.

---

## Phase 1 Architecture & Core Concepts

Phase 1 establishes the foundational workflow for incoming message ingestion, multi-intent classification (7+ intents), role-based authorization, and conditional routing.

### Workflow Graph

```text
[START]
   │
   ▼
[Receive Message Node]  --> (Validates message payload and initializes trace)
   │
   ▼
[Classify Intent Node]  --> (OpenRouter LLM with Structured Output)
   │
   ▼
[Intent Router Node]    --> (Evaluates Role-Based Access Control matrix)
   │
   ├── (Authorized)   --> Specialized Response Node (Greeting, Knowledge, Tickets, Admin DB, etc.)
   └── (Unauthorized) --> Handle Unauthorized Node (403 Forbidden Response)
   │
   ▼
 [END]
```

---

## Supported Roles & Permissions (RBAC Matrix)

| Role | Permitted Actions |
| :--- | :--- |
| **Customer** | Knowledge Base Search (`knowledge_search`), Check Own Tickets (`my_tickets_search`), Greetings (`greeting`) |
| **Support Agent** | All Customer permissions + Ticket Management (`ticket_create_update`) + External API Status (`external_api_search`) |
| **Senior Agent** | All Support Agent permissions + Sensitive System Operations (`sensitive_operation`) |
| **Admin** | Unrestricted access + Direct Database Queries & Operations (`database_query_operation`) |

---

## 8 Supported Intents

1. `greeting`: Standard greetings, introductions, and pleasantries.
2. `knowledge_search`: Technical troubleshooting, corporate IT policies, VPN and network guides.
3. `my_tickets_search`: Checking status of user's own tickets.
4. `ticket_create_update`: Creating or modifying support tickets.
5. `external_api_search`: Querying third-party vendor status or documentation.
6. `sensitive_operation`: Password resets, permission elevation, system reboot.
7. `database_query_operation`: Direct database schema queries and data maintenance (Admin only).
8. `out_of_scope`: General fallback for unrelated questions.

---

## Project Structure

```text
ldc-Langgraph/
│
├── app/
│   ├── agent/                 # LangGraph workflow logic
│   │   ├── edges/             # Conditional routing rules
│   │   ├── nodes/             # Node implementations (Receive, Classify, Router, Responses)
│   │   ├── prompts/           # Structured classification prompts
│   │   ├── graph.py           # Compiled StateGraph instance
│   │   └── state.py           # AgentState TypedDict definition
│   │
│   ├── api/                   # FastAPI REST API Layer
│   │   ├── middlewares/       # Request logging and unified error handlers
│   │   ├── v1/
│   │   │   ├── endpoints/     # Auth and Chat endpoints
│   │   │   └── router.py      # v1 router aggregator
│   │   └── dependencies.py    # JWT validation and role guards
│   │
│   ├── core/                  # Infrastructure & configuration
│   │   ├── config.py          # Pydantic Settings with .env loading
│   │   ├── logging.py         # Structured logging setup
│   │   └── security.py        # Bcrypt and JWT utilities
│   │
│   ├── schemas/               # Pydantic contracts & enums
│   │   ├── auth_schema.py     # Role and token schemas
│   │   ├── chat_schema.py     # Request and response models
│   │   └── intent_schema.py   # Intent enum and structured output model
│   │
│   ├── services/
│   │   └── llm_service.py     # OpenRouter ChatOpenAI service
│   │
│   └── main.py                # FastAPI Application Factory
│
├── tests/
│   ├── unit/                  # Unit tests for intents, RBAC, and security
│   ├── integration/           # Integration tests for API endpoints
│   └── conftest.py            # Pytest fixtures and mock tokens
│
├── docs/                      # Architectural documentation
├── .env.example               # Environment variables template
├── requirements.txt           # Verified dependencies
└── pytest.ini                 # Test suite configuration
```

---

## Quickstart Guide

### 1. Environment Setup

```bash
# In Linux / WSL:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the template and provide your OpenRouter API key:

```bash
cp .env.example .env
```

Edit `.env` to set:
```env
OPENROUTER_API_KEY="sk-or-v1-your-actual-api-key"
DEFAULT_MODEL="qwen/qwen-2.5-72b-instruct"
```

### 3. Run the FastAPI Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* Interactive Swagger Docs: `http://localhost:8000/docs`
* Health Check Endpoint: `http://localhost:8000/health`

---

## Running the Automated Test Suite

```bash
pytest -v
```

Or run the standalone runner:

```bash
python tests/runner.py
```
