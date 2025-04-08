# Rocket Launch GenAI Platform - Docker Installation Guide

This guide provides detailed step-by-step instructions for setting up the Rocket Launch GenAI Platform using Docker and Docker Compose, which is the recommended deployment method.

For local installation *without* Docker, see [`LOCAL_INSTALLATION.md`](LOCAL_INSTALLATION.md).

## Prerequisites

- **Git:** To clone the repository.
- **Docker Engine:** Version 24.0+ (or Docker Desktop equivalent). [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose:** Version v2.0+ (usually included with Docker Desktop). [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Text Editor/IDE:** For editing configuration files (e.g., VS Code).
- **Web Browser:** For accessing the frontend application and API docs.
- **(Optional) API Keys:** If you plan to use external services like OpenAI or Anthropic.
- **System Resources:** 4GB+ RAM available for containers, 10GB+ free disk space.

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rocket-launch-genai
```

### 2. Create Initial Database Schema (Optional - if not handled by init script)

If your PostgreSQL container setup doesn't automatically run an initialization script, create an `init.sql` file in the project root directory. This script typically sets up the initial role and database.

Example `init.sql`:

```sql
CREATE ROLE rocket WITH LOGIN PASSWORD 'rocket123';
ALTER ROLE rocket CREATEDB;
CREATE DATABASE rocket_launch_genai;
\c rocket_launch_genai
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL PRIVILEGES ON DATABASE rocket_launch_genai TO rocket;
```

### 3. Configure Environment Variables

The platform uses environment variables for configuration. See [CONFIGURATION.md](CONFIGURATION.md) for a detailed explanation of all variables and how different `.env` files are used for Docker vs. local setups.

**Summary for Docker:**
- Copy `root .env.example` to `root .env` and configure shared variables (DB credentials, API keys).
- Review service-specific `.env.development` / `.env.production` files (backend & frontend).
- **Do not** use `.env.local` files with Docker.

### 4. Build and Start Containers

Open your terminal in the root directory (`rocket-launch-genai`) where the `docker-compose.yml` file is located.

-   **For Development (uses `docker-compose.override.yml`, includes hot-reloading):**
    ```bash
    # Build images (if needed) and start services in detached mode
    docker-compose up -d --build

    # View logs during startup
    docker-compose logs -f
    ```
    The `--build` flag ensures images are rebuilt if Dockerfiles or context change. Omit it for faster subsequent starts if code hasn't changed.

-   **For Production (uses `docker-compose.prod.yml`, optimized builds):**
    ```bash
    # Ensure .env.production files are correctly configured
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
    ```
    The `-d` flag runs containers in the background.

### 5. Database Migrations (First Time Setup / After Model Changes)

After the containers are running (especially the `postgres` and `backend` services), apply the database schema migrations using Alembic.

-   Find the name of your running backend container (usually ends with `-backend-1`):
    ```bash
    docker-compose ps
    ```
-   Execute the Alembic command inside the backend container:
    ```bash
    docker-compose exec backend alembic upgrade head
    ```
    *Note:* Some setups might run migrations automatically via an entrypoint script. Check the backend's `Dockerfile` or associated scripts if unsure. You may need to run this again after updating backend models.

### 6. Accessing the Platform

After successful deployment, the services will be available at:

- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555)

Default admin login:
- Email: admin@example.com
- Password: password (set via `INITIAL_ADMIN_PASSWORD` in `backend/.env.development`)

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
   - Ensure strong secrets (`SECRET_KEY`, `INITIAL_ADMIN_PASSWORD`, `NEXTAUTH_SECRET`, `REDIS_PASSWORD`).
   - Set `ENVIRONMENT=production`, `NODE_ENV=production`.
   - Adjust `LOG_LEVEL` (e.g., `INFO` or `WARNING`).
   - Configure correct production URLs.
- `frontend/.env.production`

Do NOT copy these files to `.env.local`, as docker-compose.prod.yml is configured to use the `.env.production` files directly.

## Environment File Usage Summary

See [CONFIGURATION.md](CONFIGURATION.md) for details on which files are used and the purpose of each variable.

| Environment          | Root File Used | Frontend File Used | Backend File Used | Start Command Suffix                                           |
| -------------------- | -------------- | ------------------ | ----------------- | -------------------------------------------------------------- |
| Local Dev (no Docker) | N/A            | `.env.local`       | `.env.local`      | (See `LOCAL_INSTALLATION.md`)                                  |
| Docker Development   | `.env`         | `.env.development` | `.env.development`| `up -d` (uses override)                                        |
| Docker Production    | `.env`         | `.env.production`  | `.env.production` | `-f docker-compose.yml -f docker-compose.prod.yml up -d` |

**Important:**
- `.env.local` files are **only** for local development without Docker.
- The root `.env` file provides shared variables referenced within the service-specific `.env.*` files and by Docker Compose itself.

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

If Redis requires a password:
```bash
# Check Redis container
docker-compose ps redis

# Test Redis connection with password
docker-compose exec redis redis-cli -a ${REDIS_PASSWORD} ping
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