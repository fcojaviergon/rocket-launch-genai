# Technical and Functional Specification: Rocket Launch GenAI Platform

## 1. General System Description

**Rocket Launch GenAI Platform** is a modular white-label platform designed to accelerate the development of enterprise applications based on artificial intelligence. Its event-driven, microservices-based architecture allows efficient scaling and extension for different domains and use cases. The platform is designed for developers, data teams, and businesses that need to create intelligent processing solutions, AI queries, and data flow automation.

## 2. Main Functionalities

### 2.1 Document Management

- Upload and storage of documents (PDF, DOCX, TXT, etc.)
- Text extraction, segmentation by chunks
- Generation of embeddings and storage in `pgvector`
- Document processing through configurable pipelines

### 2.2 AI Queries and Semantic Search

- Completions view: model selection and response generation
- Chat view: creation of chats with persistent history
- Messages view: query of processed documents through semantic search
- Documents view: visualization of uploaded files and their metadata

### 2.3 Pipeline Design

- Creation of visual flows with draggable nodes (future UI)
- Modular configuration of steps: input, processing, output
- Possibility of manual or automatic execution when uploading documents
- In the future: pre-configured pipeline templates by document type

### 2.4 Control Panel and Analytics

- Dashboard with usage metrics by user, document, and pipeline
- Visualization of performance, response times, and errors
- Estimation of token consumption and costs
- Export of reports

### 2.5 Security and Access

- Authentication with JWT and sessions (NextAuth)
- Role and permission system (RBAC)
- Available roles:
  - **Super Admin**: Full access, cannot be deleted by other roles
  - **Admin**: Can manage users, documents, and configurations
  - **User**: Can operate on their documents, execute AI, manage their personal data
- Audit of relevant events and actions

## 3. Technical Architecture

### 3.1 Vision

The Rocket Launch GenAI Platform architecture implements an event-driven communication pattern with decoupled components. This separation allows high internal cohesion and low coupling between modules, facilitating system maintenance and extensibility.

### 3.2 Backend

- **Framework:** FastAPI + Python 3.12
- **Database:** PostgreSQL 16+ with pgvector
- **ORM:** SQLAlchemy 2.0+ + Alembic
- **Asynchronous tasks:** Redis + Celery
- **AI:** Integration with OpenAI / HuggingFace / local models
- **Document processing:** OpenCV for content analysis
- **Authentication:** JWT implementation with jose library
- **Data Validation:** Pydantic v2

### 3.3 Frontend

- **UI Framework:** Next.js 14+ with TypeScript
- **Style:** Tailwind CSS + Radix UI
- **Authentication:** NextAuth with JWT
- **State:** React Context and hooks
- **Real-time:** SSE (Server-Sent Events)
- **Routing:** Next.js App Router with nested routes and shared layouts
- **Testing:** Jest (unit) + Playwright (e2e)

### 3.4 Communication and Flows

- API Gateway in FastAPI
- Event bus in Redis
- Decoupled workers for domain processing (documents, embeddings, AI, etc.)

### 3.5 System Architecture Diagram

1. **Web Client (Next.js)**:
   - User interface based on Next.js
   - Communicates with the backend through the API Gateway

2. **API Gateway (FastAPI)**:
   - Manages all HTTP requests
   - Implemented with FastAPI
   - Coordinates communication between the client and backend services

3. **AI Services**:
   - RAG (Retrieval Augmented Generation) components
   - Pipeline system for AI workflows

4. **PostgreSQL + pgvector**:
   - Main system database
   - Uses the pgvector extension for vector storage and search

5. **Redis (Event Bus)**:
   - Messaging system for asynchronous communication
   - Implements the event bus pattern
   - Facilitates decoupling between components

6. **Celery Workers**:
   - Asynchronous task processing
   - Handles resource-intensive operations

7. **AI Providers**:
   - Integration with external services such as OpenAI
   - Provides language model capabilities and embedding generation

## 4. Modular Structure

### 4.1 Backend Folder Organization

```
backend/
├── alembic/                     # Database migrations
│   └── versions/                # Migration versions
├── api/                         # API endpoint definitions
│   └── v1/                      # API version 1
│       ├── api.py               # Main API router
│       ├── auth.py              # Authentication endpoints
│       ├── chat.py              # Chat endpoints
│       ├── completions.py       # Completions endpoints
│       ├── document.py          # Document endpoints
│       ├── pipeline_simplified.py # Pipeline endpoints
│       └── users.py             # User endpoints
├── core/                        # Central configuration
│   ├── config.py                # Application configurations
│   ├── deps.py                  # Dependencies (injection)
│   ├── events/                  # Event system
│   └── security.py              # Security functions
├── database/                    # Data access layer
│   ├── crud/                    # CRUD operations
│   ├── models/                  # ORM models
│   │   ├── base.py              # Base model class
│   │   ├── conversation.py      # Conversation model
│   │   ├── document.py          # Document model
│   │   ├── pipeline.py          # Pipeline model
│   │   └── user.py              # User model
│   └── session.py               # DB session management
├── main.py                      # FastAPI entry point
├── test/                        # Test suite
├── modules/                     # Business modules
│   ├── auth/                    # Authentication logic
│   ├── document/                # Document processing
│   ├── pipeline/                # Pipeline module
│   │   ├── config/              # Pipeline configs
│   │   ├── base.py              # Pipeline base class
│   │   ├── data_steps.py        # Data processing steps
│   │   ├── document_steps.py    # Document steps
│   │   ├── embedding_steps.py   # Embedding steps
│   │   └── image_steps.py       # Image steps
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
```

### 4.2 Frontend Organization

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

## 5. Priority Use Cases

1. A user uploads a document and processes it with a pipeline  
2. A user queries documents through messages with AI  
3. A user generates responses with an LLM model from completions  
4. A user interacts with a chatbot with history  
5. An administrator manages users and permissions  
6. A super admin supervises all system activity  

## 6. Implementation Roadmap

| Phase | Key Deliverables                                   |
|-------|---------------------------------------------------|
| P1    | Authentication module and user management         |
| P2    | Document module + processing + embeddings         |
| P3    | Completions view + LLM model integration          |
| P4    | Messages view + vector search + RAG               |
| P5    | Chat module with persistent history               |
| P6    | Configurable pipeline engine and view             |
| P7    | System dashboard and metrics                      |
| P8    | Roles, permissions, and general refinements       |

## 7. Final Considerations

This specification aims to serve as an implementation guide and progress control. The technical components are designed to decouple responsibilities, facilitate scalability, and allow future customization by clients or integrators. The modular approach allows the system to evolve without affecting its core.

## 8. White-Labeling and Customization

The Rocket Launch GenAI Platform is designed with white-labeling in mind, allowing licensees to adapt it for their specific branding and needs.

### 8.1 Configuration

- **Environment Variables:** Core settings, API keys, database connections, and feature toggles are managed through environment variables (primarily in the root `.env` file when using Docker Compose). This allows easy configuration without code changes.
- **Backend Settings:** The `backend/core/config.py` file defines the structure for settings loaded from environment variables, providing a central place to understand configuration options.

### 8.2 Frontend Customization

- **Theming:** Modify `frontend/tailwind.config.ts` and `frontend/src/app/globals.css` to change colors, fonts, spacing, and overall visual appearance to match brand guidelines.
- **Branding Assets:** Replace logo files and favicons located in `frontend/public/`. Update references to these assets within the React components.
- **Text Content:** Modify user-facing text directly within the React components. For multi-language support, integrating an internationalization (i18n) library is recommended.

### 8.3 Backend Extensibility

- **Modular Design:** The backend's structure in `backend/modules/` allows for adding new features or modifying existing ones in a relatively isolated manner.
- **Service Integration:** New external services can be integrated by adding configurations in `core/config.py` and creating new service clients within `backend/services/`.

### 8.4 Deployment

- **Docker:** The use of Docker and Docker Compose facilitates deploying customized versions of the platform consistently across different environments.
- **Environment Configuration:** Separate `.env.development` and `.env.production` files provide environment-specific configurations.


