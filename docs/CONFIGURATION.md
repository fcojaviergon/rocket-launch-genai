# Configuration

This document outlines the environment variables used to configure the Rocket Launch GenAI Platform for both Docker and local (non-Docker) setups.

## Overview

Configuration is managed primarily through environment variables loaded from different `.env` files depending on the environment:

- **Docker Development:** Uses `root .env` for shared variables + `backend/.env.development` + `frontend/.env.development`.
- **Docker Production:** Uses `root .env` for shared variables + `backend/.env.production` + `frontend/.env.production`.
- **Local Development:** Uses `backend/.env.local` + `frontend/.env.local`.

**Important:**
- `.env.local` files are **only** used for local development without Docker.
- For Docker setups, the `root .env` file provides shared variables (like database credentials) which are often referenced within the service-specific `.env.*` files (e.g., `${POSTGRES_USER}`).
- Always ensure strong, unique secrets for production environments (`SECRET_KEY`, `NEXTAUTH_SECRET`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`).

## Root `.env` File (Docker Only)

These variables are typically placed in the `root .env` file (copied from `.env.example`) when using Docker Compose. They provide shared values used by different services.

| Variable             | Example Value           | Description                                                                   |
| -------------------- | ----------------------- | ----------------------------------------------------------------------------- |
| `POSTGRES_USER`      | `postgres`              | Username for the PostgreSQL database.                                         |
| `POSTGRES_PASSWORD`  | `your_strong_password`  | Password for the PostgreSQL user. **Set a strong password.**                  |
| `POSTGRES_DB`        | `rocket_launch_genai`   | Name of the PostgreSQL database to use or create.                             |
| `REDIS_PASSWORD`     | `your_strong_password`  | (Optional) Password for the Redis instance. **Set a strong password.**        |
| `OPENAI_API_KEY`     | `sk-proj-xxxxxxxxxx`    | (Optional) API key for OpenAI services.                                       |
| `ANTHROPIC_API_KEY`  | `sk-ant-api03-xxxx`     | (Optional) API key for Anthropic services.                                    |
| `COMPOSE_PROJECT_NAME`| `rocket_launch`        | (Optional) Name prefix for Docker containers and networks.                    |
| `TZ`                 | `UTC`                   | (Optional) Timezone setting for containers (e.g., `America/New_York`).         |

## Backend Configuration (`backend/.env.*`)

These variables configure the FastAPI backend application.

| Variable                      | Example (Dev)                 | Example (Prod)                | Description                                                                                                 | Local Only? |
| ----------------------------- | ----------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------- |
| `DATABASE_URL`                | `postgresql+asyncpg://...`    | `postgresql+asyncpg://...`    | Full database connection string. Use `localhost` for local, `postgres` (service name) for Docker.             | No          |
| `REDIS_URL`                   | `redis://localhost:6379/0`    | `redis://:password@redis:6379/0`| Full Redis connection string for broker/cache. Include password if set. Use `localhost`/`redis`.            | No          |
| `CELERY_BROKER_URL`           | `redis://localhost:6379/0`    | `redis://:password@redis:6379/0`| Celery: Connection URL for the message broker (Redis).                                                       | No          |
| `CELERY_RESULT_BACKEND`       | `redis://localhost:6379/1`    | `redis://:password@redis:6379/1`| Celery: Connection URL for storing task results (Redis, different DB index).                                | No          |
| `SECRET_KEY`                  | `your_dev_secret_key`         | `your_strong_production_key`  | Secret key for signing JWT tokens. **Must be strong and unique for production.**                              | No          |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                          | `60`                          | Lifetime of JWT access tokens in minutes.                                                                   | No          |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                           | `30`                          | Lifetime of JWT refresh tokens in days.                                                                     | No          |
| `JWT_ALGORITHM`               | `HS256`                       | `HS256`                       | Algorithm used for JWT signing.                                                                             | No          |
| `INITIAL_ADMIN_EMAIL`         | `admin@example.com`           | `admin@yourdomain.com`        | Email address for the first admin user created automatically.                                             | No          |
| `INITIAL_ADMIN_PASSWORD`      | `password`                    | `strong_admin_password`       | Password for the first admin user. **Must be strong for production.**                                       | No          |
| `ENVIRONMENT`                 | `development`                 | `production`                  | Application environment mode (`development`, `production`). Affects logging, debugging, etc.                | No          |
| `AI_PROVIDER`                 | `openai`                      | `openai`                      | Default AI provider to use (`openai`, `anthropic`, etc. - depends on integration).                          | No          |
| `DEFAULT_CHAT_MODEL`          | `gpt-4o-mini`                 | `gpt-4o`                      | Default model identifier for chat completions.                                                              | No          |
| `DEFAULT_EMBEDDING_MODEL`     | `text-embedding-3-small`      | `text-embedding-3-large`      | Default model identifier for generating text embeddings.                                                    | No          |
| `LOG_LEVEL`                   | `DEBUG`                       | `INFO`                        | Logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`).                                                    | No          |
| `LOG_DIR`                     | `logs`                        | `/var/log/app` (example)      | Directory to store log files.                                                                               | No          |
| `CELERY_WORKER_CONCURRENCY`   | `4`                           | `8` (example)                 | Celery: Number of concurrent worker processes.                                                              | No          |
| `CELERY_WORKER_POOL`          | `prefork`                     | `prefork`                     | Celery: Worker execution pool type.                                                                         | No          |
| `POSTGRES_USER`               | `user`                        | -                             | DB Username. **Only needed for `.env.local`** if not using full `DATABASE_URL`.                             | Yes         |
| `POSTGRES_PASSWORD`           | `password`                    | -                             | DB Password. **Only needed for `.env.local`** if not using full `DATABASE_URL`.                             | Yes         |
| `POSTGRES_HOST`               | `host`                        | -                             | DB Host. **Only needed for `.env.local`** if not using full `DATABASE_URL`.                                 | Yes         |
| `POSTGRES_DB`                 | `dbname`                      | -                             | DB Name. **Only needed for `.env.local`** if not using full `DATABASE_URL`.                                 | Yes         |

**Note on `DATABASE_URL` and `REDIS_URL`:**
- For **Local Development (.env.local):** Use `localhost` as the host.
- For **Docker Development (.env.development):** Use the service name (`postgres`, `redis`) as the host and reference root `.env` variables (e.g., `redis://:${REDIS_PASSWORD}@redis:6379/0`).
- For **Docker Production (.env.production):** Similar to Docker Dev, using service names and potentially referencing root `.env` variables.

## Frontend Configuration (`frontend/.env.*`)

These variables configure the Next.js frontend application. Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

| Variable                                | Example (Dev)                 | Example (Prod)                 | Description                                                                                                  | Exposed? |
| --------------------------------------- | ----------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------ | -------- |
| `NEXT_PUBLIC_BACKEND_URL`               | `http://localhost:8000`       | `https://api.yourdomain.com`   | Base URL of the backend API accessible *from the user's browser*.                                          | Yes      |
| `NEXT_PUBLIC_API_URL`                   | `http://localhost:8000/api`   | `https://api.yourdomain.com/api`| Full URL for the primary API endpoint used by the client-side code.                                        | Yes      |
| `NEXT_PUBLIC_API_VERSION`               | `v1`                          | `v1`                           | API version prefix (prepended to API calls).                                                               | Yes      |
| `NEXT_PUBLIC_ACCESS_TOKEN_EXPIRE_MINUTES`| `30`                         | `60`                          | (Optional) Hint for frontend UI about token expiry. Does not control actual token lifetime (backend does). | Yes      |
| `INTERNAL_BACKEND_URL`                  | `http://backend:8000`         | `http://backend:8000`          | Base URL used by the frontend *server* (Next.js API routes, SSR) to talk to the backend within Docker.       | No       |
| `NEXTAUTH_URL`                          | `http://localhost:3000`       | `https://app.yourdomain.com`   | Full canonical URL of the frontend application. Crucial for NextAuth redirects.                            | No       |
| `NEXTAUTH_SECRET`                       | `your_dev_secret_key`         | `your_strong_production_secret`| Secret used by NextAuth.js for session encryption, JWT signing, etc. **Must be strong for production.**    | No       |
| `NODE_ENV`                              | `development`                 | `production`                   | Node.js environment mode (`development`, `production`). Affects Next.js behavior.                           | No       |

**Note on URLs:**
- `NEXT_PUBLIC_BACKEND_URL` is what the user's browser connects to.
- `INTERNAL_BACKEND_URL` is only used for server-to-server communication within the Docker network (e.g., from a Next.js API route to the FastAPI backend). It's not needed for local non-Docker setup. 