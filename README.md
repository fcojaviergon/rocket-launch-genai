# Rocket Launch GenAI Platform

An enterprise-ready boilerplate for building AI-powered applications with document processing, semantic search, and RAG capabilities.

## Project Overview

The Rocket Launch GenAI Platform provides a modular, white-label solution for developing intelligent applications leveraging:

- Document processing and semantic search
- AI completions and conversational interfaces
- Retrieval Augmented Generation (RAG)
- Event-driven microservices architecture

## Project Structure

- `backend/` - FastAPI backend with PostgreSQL, pgvector, and Celery workers
- `frontend/` - Next.js 14+ frontend with TypeScript and Tailwind CSS
- `scripts/` - Utility scripts for project management
- `docker-compose.yml` - Container orchestration for development and production

## Installation

Choose your preferred installation method:

- [Docker Installation Guide](DOCKER_INSTALLATION.md) (Recommended)
- [Local Installation Guide](LOCAL_INSTALLATION.md)

## Quick Links

After installation, access the following services:

- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Celery Flower Dashboard: http://localhost:5555

## Development

- Backend API documentation provides interactive endpoints via Swagger UI
- Frontend includes hot-reloading for rapid development
- Backend includes auto-reload during development
- PostgreSQL with pgvector extension for efficient vector search
- Redis for both event bus and task queue functionalities

Note: Server execution is managed by the project owner. Once installation is complete, notify them to refresh the servers.

## Documentation

- [Functional & Technical Specification](FUNCTIONAL_TECH_SSF.md)
- [Step-by-Step Tutorial](TUTORIAL.md)
- [Development Roadmap](ROADMAP.md)
- [Installation Guide](INSTALLATION_GUIDE.md)

## License

[License](LICENSE) 