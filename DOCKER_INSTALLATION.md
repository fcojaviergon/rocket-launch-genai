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

Copy the example environment files:

```bash
cp .env.example .env
cp frontend/.env.development frontend/.env.local
cp backend/.env.development backend/.env.local
```

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

##### Backend `.env.local`:
```env
DATABASE_URL=postgresql://rocket:rocket123@postgres:5432/rocket_launch_genai
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=password
```

##### Frontend `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret_here
```

### 5. Build and Start Containers

```bash
# Start all services
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
- Password: password (as set in backend/.env.local)

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
# Copy production env files
cp frontend/.env.production frontend/.env.local
cp backend/.env.production backend/.env.local

# Start with production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

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