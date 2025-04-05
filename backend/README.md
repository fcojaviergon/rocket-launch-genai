# Rocket Launch GenAI Platform - Backend

This directory contains the backend application for the Rocket Launch GenAI Platform, built with FastAPI, Python, PostgreSQL (with pgvector), Redis, and Celery.

## Overview

The backend provides the core API, data processing, and AI integration capabilities for the platform through an event-driven, modular architecture.

Key responsibilities include:

- RESTful API endpoints for frontend and external client integration
- User authentication and role-based access control
- Document processing and embedding generation pipeline
- Vector storage and semantic search using pgvector
- AI model integration (completions, chat, embeddings)
- Background task processing via Celery workers
- Event-driven architecture using Redis pub/sub

## Tech Stack

- **Framework:** FastAPI (ASGI)
- **Language:** Python 3.12+
- **Database:** PostgreSQL 16+ with pgvector extension
- **ORM:** SQLAlchemy 2.0+ with Alembic for migrations
- **Task Queue:** Celery with Redis as the broker and results backend
- **Event Bus:** Redis Pub/Sub
- **Authentication:** JWT + Password Hashing (passlib)
- **Data Validation:** Pydantic v2
- **AI Integrations:** OpenAI, Hugging Face, local models
- **Testing:** Pytest for unit and integration tests

## Project Structure

```
backend/
├── alembic/              # Database migrations
├── api/                  # API endpoints organized by version
│   └── v1/               # API version 1 routes
├── core/                 # Core configuration and utilities
│   ├── config.py         # Application settings
│   ├── deps.py           # Dependency injection
│   ├── events/           # Event system
│   └── security.py       # Authentication and security
├── database/             # Database models and operations
│   ├── crud/             # CRUD operations for models
│   ├── models/           # SQLAlchemy ORM models
│   └── session.py        # DB session management
├── modules/              # Business logic modules
│   ├── auth/             # Authentication logic
│   ├── document/         # Document processing
│   ├── pipeline/         # Pipeline orchestration
│   └── rag/              # Retrieval Augmented Generation
├── schemas/              # Pydantic models for validation
├── services/             # External service integrations
│   └── ai/               # AI provider interfaces
├── tasks/                # Celery task definitions
├── test/                 # Test suite
├── storage/              # File storage location
├── logs/                 # Application logs
├── Dockerfile            # Container definition for API
├── Dockerfile.worker     # Container definition for workers
├── requirements.txt      # Python dependencies
├── main.py               # Application entry point
├── run.py                # Development server runner
├── start_worker.sh       # Script to start Celery workers
└── start_flower.sh       # Script to start Flower monitoring
```

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ with pgvector extension installed
- Redis server
- Required API keys for AI services (if using external providers)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd rocket-launch-genai/backend
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   - Copy `.env.development` to `.env.local`
   - Set required variables:
     - `DATABASE_URL`: PostgreSQL connection string
     - `REDIS_URL`: Redis connection string
     - `SECRET_KEY`: JWT signing key
     - `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD`: Admin credentials
     - AI service API keys (e.g., `OPENAI_API_KEY`)

5. **Set up the Database:**
   - Ensure PostgreSQL is running with pgvector extension
   - Run migrations:
     ```bash
     alembic upgrade head
     ```

### Running the Development Server

Start the FastAPI server:
```bash
python run.py
```

The API will be available at http://localhost:8000 with documentation at http://localhost:8000/docs.

### Running Celery Workers

In a separate terminal:
```bash
bash start_worker.sh
```

### Running Flower (Monitoring Dashboard)

In a separate terminal:
```bash
bash start_flower.sh
```

Access the Flower dashboard at http://localhost:5555.

## API Documentation

The API is self-documenting with OpenAPI:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Docker Deployment

The backend includes Dockerfiles for both the API and worker services:

```bash
# Build API container
docker build -t rocket-launch-backend -f Dockerfile .

# Build worker container
docker build -t rocket-launch-worker -f Dockerfile.worker .
```

For full deployment, use the root docker-compose.yml file.

## Testing

Run the test suite with:

```bash
pytest
```

For specific test modules:

```bash
pytest test/test_document.py
```

## Development Guidelines

- Follow Python PEP 8 style guidelines
- Use SQLAlchemy 2.0 style for database operations
- Write unit tests for new features
- Use dependency injection pattern with FastAPI
- Follow RESTful API design principles
- Document API endpoints with docstrings 