# Docker Installation Guide

This guide provides step-by-step instructions for setting up the Rocket Launch GenAI Platform using Docker and Docker Compose, which is the recommended deployment method.

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.0+
- Git
- 4GB+ RAM available for containers
- 10GB+ free disk space

## Installation Steps

### 1. Install Docker

Choose the appropriate installation method for your operating system:

- **macOS**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Windows**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux**: Follow the [Docker Engine installation guide](https://docs.docker.com/engine/install/)

Verify installation:
```bash
docker --version
docker-compose --version
```

### 2. Clone the Repository

```bash
git clone <repository-url>
cd rocket-launch-genai
```

### 3. Database Initialization

Create `init.sql` in the project root directory with the following content:

```sql
CREATE ROLE rocket WITH LOGIN PASSWORD 'rocket123';
ALTER ROLE rocket CREATEDB;
CREATE DATABASE rocket_launch_genai;
\c rocket_launch_genai
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL PRIVILEGES ON DATABASE rocket_launch_genai TO rocket;
```

### 4. Configure Environment Variables

For Docker installations, you only need to copy the root .env file:

```bash
# Only copy the root .env file for global variables
cp .env.example .env
```

The environment files for each service are already configured:
- `backend/.env.development` - For Docker development
- `frontend/.env.development` - For Docker development
- `backend/.env.production` - For Docker production
- `frontend/.env.production` - For Docker production

These files do NOT need to be copied to .env.local, as Docker Compose will use them automatically.

#### Key Environment Variables:

##### Root `.env`:
```env
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=rocket_launch_genai

# Redis
REDIS_PASSWORD=redis123

# API Keys (if needed)
OPENAI_API_KEY=your_openai_key
```

##### Check backend/.env.development:
```env
# URLs use Docker service names
DATABASE_URL=postgresql+asyncpg://rocket:rocket123@postgres:5432/rocket_launch_genai
REDIS_URL=redis://redis:6379/0
```

##### Check frontend/.env.development:
```env
# URLs for internal and external connections
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
INTERNAL_BACKEND_URL=http://backend:8000
```

### 5. Build and Start Containers

```bash
# Start all services in development mode
# This will automatically use the .env.development files
docker-compose up -d

# View logs during startup
docker-compose logs -f
```

The initial build may take several minutes depending on your internet connection and system performance.

## Accessing the Platform

After successful deployment, the services will be available at:

- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555)

Default admin login:
- Email: admin@example.com
- Password: password (/backend/database/init_db.py definition)

## Common Docker Commands

```bash
# View all container status
docker-compose ps

# View logs for all services
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart frontend

# Rebuild and restart services (after code changes)
docker-compose up -d --build
```

## Production Deployment

For production deployment, use the production configuration:

```bash
# Start with production configuration
# This will automatically use the .env.production files
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Make sure to review and update the production environment files before deployment:
- `backend/.env.production`
- `frontend/.env.production`

Do NOT copy these files to .env.local, as docker-compose.prod.yml is configured to use the .env.production files directly.

## Environment File Usage Guide

| Environment | Root File | Frontend File | Backend File | Command |
|-------------|-----------|---------------|--------------|---------|
| Local Dev (no Docker) | N/A | .env.local | .env.local | See LOCAL_INSTALLATION.md |
| Docker Development | .env | .env.development | .env.development | docker-compose up -d |
| Docker Production | .env | .env.production | .env.production | docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d |

**Important:** The .env.local files are only for local development without Docker. Do not rename or copy files to .env.local for Docker deployments.

## Troubleshooting

### Database Connection Issues

If the backend cannot connect to the database:

```bash
# Check if postgres container is running
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres

# Verify database initialization
docker-compose exec postgres psql -U postgres -d rocket_launch_genai -c "\dx"

# Check user permissions
docker-compose exec postgres psql -U postgres -d rocket_launch_genai -c "\du"
```

### Redis Connection Issues

```bash
# Check Redis container
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

### Port Conflicts

If you encounter port conflicts:

1. Check for processes using the same ports:
   ```bash
   # On Linux/macOS
   lsof -i :3000
   lsof -i :8000
   
   # On Windows
   netstat -ano | findstr :3000
   netstat -ano | findstr :8000
   ```

2. Modify port mappings in `docker-compose.yml` if needed:
   ```yaml
   ports:
     - "3001:3000"  # Map host port 3001 to container port 3000
   ```

### Container Health Checks

```bash
# Check frontend container health
docker inspect --format "{{json .State.Health }}" rocket-launch-genai-frontend-1

# Check backend container health
docker inspect --format "{{json .State.Health }}" rocket-launch-genai-backend-1
```

Note: Server execution is managed by the project owner. Once installation is complete, notify them to refresh the servers. 