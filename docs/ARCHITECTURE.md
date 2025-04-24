# Technical Architecture

## Vision

The Rocket Launch GenAI Platform architecture implements an event-driven communication pattern with decoupled components. This separation allows high internal cohesion and low coupling between modules, facilitating system maintenance and extensibility.

## Technology Stack

### Backend

- **Framework:** FastAPI + Python 3.12
- **Database:** PostgreSQL 16+ with pgvector
- **ORM:** SQLAlchemy 2.0+ + Alembic
- **Asynchronous tasks:** Redis + Celery
- **AI:** Integration with OpenAI / HuggingFace / local models
- **Document processing:** OpenCV for content analysis
- **Authentication:** JWT implementation with jose library
- **Data Validation:** Pydantic v2

### Frontend

- **UI Framework:** Next.js 14+ with TypeScript
- **Style:** Tailwind CSS + Radix UI
- **Authentication:** NextAuth with JWT
- **State:** React Context and hooks
- **Real-time:** SSE (Server-Sent Events)
- **Routing:** Next.js App Router with nested routes and shared layouts
- **Testing:** Jest (unit) + Playwright (e2e)

## Communication and Flows

- API Gateway in FastAPI
- Unified event management system combining internal event bus and Redis-based real-time notifications
- Decoupled processors for domain processing (documents, embeddings, RFP analysis, proposal analysis, etc.)
- Asynchronous task processing with Celery

## System Architecture Diagram

1.  **Web Client (Next.js)**:
    -   User interface based on Next.js
    -   Communicates with the backend through the API Gateway

2.  **API Gateway (FastAPI)**:
    -   Manages all HTTP requests
    -   Implemented with FastAPI
    -   Coordinates communication between the client and backend services

3.  **AI Services**:
    -   RAG (Retrieval Augmented Generation) components
    -   Pipeline system for AI workflows

4.  **PostgreSQL + pgvector**:
    -   Main system database
    -   Uses the pgvector extension for vector storage and search

5.  **Redis (Event Bus)**:
    -   Messaging system for asynchronous communication
    -   Implements the unified event management system
    -   Supports both internal event bus and real-time notifications
    -   Facilitates decoupling between components

6.  **Celery Workers**:
    -   Asynchronous task processing
    -   Handles resource-intensive operations

7.  **AI Providers**:
    -   Integration with external services such as OpenAI
    -   Provides language model capabilities and embedding generation

## Modular Structure

### Backend Folder Organization

```
backend/
├── alembic/                     # Database migrations
│   └── versions/                # Migration versions
├── api/                         # API endpoint definitions
│   └── v1/                      # API version 1
│       ├── analysis.py          # Analysis endpoints
│       ├── api.py               # Main API router
│       ├── auth.py              # Authentication endpoints
│       ├── chat.py              # Chat endpoints
│       ├── completions.py       # Completions endpoints
│       ├── document.py          # Document endpoints
│       ├── tasks.py             # Task management endpoints
│       └── users.py             # User endpoints
├── core/                        # Central configuration
│   ├── config.py                # Application configurations
│   ├── deps.py                  # Dependencies (injection)
│   ├── events/                  # Unified event system
│   │   ├── __init__.py          # Event system exports
│   │   ├── bus.py               # Legacy event bus (redirects to manager)
│   │   └── manager.py           # Unified event manager implementation
│   └── security.py              # Security functions
├── database/                    # Data access layer
│   ├── models/                  # ORM models
│   │   ├── analysis.py          # Analysis models (scenarios, pipelines)
│   │   ├── analysis_document.py # Analysis-document relationships
│   │   ├── base.py              # Base model class
│   │   ├── conversation.py      # Conversation model
│   │   ├── document.py          # Document model
│   │   ├── task.py              # Task tracking model
│   │   └── user.py              # User model
│   └── session.py               # DB session management
├── main.py                      # FastAPI entry point
├── test/                        # Test suite
├── modules/                     # Business modules
│   ├── analysis/                # Analysis module
│   │   ├── processors/          # Analysis processors
│   │   │   ├── document_processor.py   # Document text extraction
│   │   │   ├── embedding_processor.py  # Embedding generation
│   │   │   ├── rfp_processor.py        # RFP analysis
│   │   │   └── proposal_processor.py   # Proposal analysis
│   │   └── service.py           # Analysis service
│   ├── auth/                    # Authentication logic
│   ├── document/                # Document management
│   ├── task/                    # Task management
│   └── rag/                     # Retrieval Augmented Generation
├── requirements.txt             # Python dependencies
├── run.py                       # Execution script
├── schemas/                     # Pydantic schemas
│   ├── auth.py                  # Authentication schemas
│   ├── chat.py                  # Chat schemas
│   ├── completion.py            # Completion schemas
│   ├── document.py              # Document schemas
│   └── pipeline.py              # Pipeline schemas
├── scripts/                     # Utility scripts
├── services/                    # External/internal services
│   └── ai/                      # AI services (OpenAI, etc)
├── start_worker.sh              # Script to start workers
├── storage/                     # File storage
│   └── documents/               # Stored documents
└── tasks/                       # Asynchronous tasks (Celery)
    ├── analysis/                # Analysis tasks
    │   ├── __init__.py          # Analysis tasks exports
    │   ├── async_rfp_tasks.py   # RFP analysis tasks
    │   └── async_proposal_tasks.py # Proposal analysis tasks
    └── worker.py                # Celery worker configuration
```

### Frontend Organization

```
frontend/
├── package.json                 # NPM dependencies and scripts
├── src/
│   ├── app/                     # Next.js App Router
│   │   ├── (auth)/              # Auth route group
│   │   │   ├── login/           # Login page
│   │   │   └── register/        # Registration page
│   │   ├── api/                 # Next.js API Routes
│   │   │   ├── auth/            # Auth endpoints (client)
│   │   │   ├── chat/            # Chat endpoints (client)
│   │   │   ├── completions/     # Completions endpoints
│   │   │   └── register/        # Registration endpoints
│   │   ├── dashboard/           # Main panel
│   │   │   ├── analytics/       # Analytics page
│   │   │   ├── batch-process/   # Batch processes
│   │   │   ├── chat/            # Chat page
│   │   │   ├── completions/     # Completions page
│   │   │   ├── documents/       # Document management
│   │   │   │   └── [id]/        # Document detail
│   │   │   ├── messages/        # Messages
│   │   │   ├── pipelines/       # Pipeline management
│   │   │   │   ├── [name]/      # Pipeline detail
│   │   │   │   └── configs/     # Pipeline configs
│   │   │   ├── settings/        # Settings
│   │   │   └── users/           # User management
│   │   ├── layout.tsx           # Main layout
│   │   ├── page.tsx             # Main page
│   │   └── globals.css          # Global styles
│   ├── components/              # React components
│   │   ├── documents/           # Document components
│   │   │   ├── list/            # Document list
│   │   │   ├── upload/          # Document upload
│   │   │   └── view/            # Document view
│   │   ├── pipelines/           # Pipeline components
│   │   │   ├── config/          # Pipeline configs
│   │   │   ├── execution/       # Pipeline execution
│   │   │   └── monitoring/      # Pipeline monitoring
│   │   ├── ui/                  # UI components
│   │   │   ├── alert/           # Alert component
│   │   │   ├── button.tsx       # Buttons
│   │   │   ├── dialog/          # Modal dialogs
│   │   │   ├── progress/        # Progress bars
│   │   │   └── table/           # Tables
│   │   ├── header.tsx           # Header
│   │   └── shell.tsx            # Application shell
│   ├── lib/                     # Utilities and helpers
│   │   ├── api/                 # API client
│   │   ├── config/              # Configurations
│   │   ├── hooks/               # Custom hooks
│   │   │   ├── auth/            # Authentication hooks
│   │   │   ├── documents/       # Document hooks
│   │   │   └── pipelines/       # Pipeline hooks
│   │   ├── services/            # Frontend services
│   │   ├── types/               # TypeScript definitions
│   │   └── utils/               # Utility functions
│   └── middleware.ts            # Next.js middleware
├── e2e/                         # End-to-end tests
├── tailwind.config.ts           # Tailwind configuration
└── tsconfig.json                # TypeScript configuration
``` 