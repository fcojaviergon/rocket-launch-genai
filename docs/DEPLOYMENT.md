# Deployment and Customization

This guide covers recommendations for deploying the Rocket Launch GenAI Platform to production environments and details on customization.

## Production Checklist

Before deploying to production:

1.  **Environment Configuration**:
    -   Ensure all secrets (`SECRET_KEY`, `NEXTAUTH_SECRET`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `INITIAL_ADMIN_PASSWORD`, API Keys) are set via environment variables or a secure vault, **not** committed to code.
    -   Verify `ENVIRONMENT=production` (backend) and `NODE_ENV=production` (frontend) are set in the appropriate `.env.production` files.
    -   Configure correct production URLs (`NEXTAUTH_URL`, `NEXT_PUBLIC_BACKEND_URL`).
    -   See [CONFIGURATION.md](CONFIGURATION.md) for full details.

2.  **Logging**:
    -   Verify log directory permissions (`backend/logs/` or configured `LOG_DIR`).
    -   Set appropriate `LOG_LEVEL` (e.g., `INFO` or `WARNING`) in `backend/.env.production`.
    -   Configure log rotation via OS tools (e.g., logrotate) or container orchestration.
    -   Set up log forwarding/aggregation (e.g., ELK, Datadog, Graylog) to collect structured JSON logs from production.

3.  **Error Handling**:
    -   Verify custom exception handlers in the backend are working.
    -   Ensure no sensitive information or tracebacks are exposed to end-users in error messages.

4.  **Performance**:
    -   Adjust Celery worker counts (`CELERY_WORKER_CONCURRENCY`) based on server capacity and expected load.
    -   Configure appropriate database connection pool sizes if needed (SQLAlchemy defaults are often sufficient).
    -   Optimize frontend build using `npm run build` or `yarn build`.

5.  **Security**:
    -   **HTTPS:** Enforce HTTPS for all connections (use a reverse proxy like Nginx or Traefik for TLS termination).
    -   **Secrets:** Manage all secrets securely.
    -   **CORS:** Verify backend CORS settings (`ALLOWED_HOSTS` if applicable, though often handled by API Gateway/proxy).
    -   **Rate Limiting:** Ensure backend rate limiting is enabled and configured appropriately for production traffic.
    -   **Security Headers:** Verify security headers (CSP, X-Frame-Options, etc.) are being set correctly (often by the backend framework or reverse proxy).
    -   **Dependencies:** Regularly update dependencies to patch security vulnerabilities.
    -   **Database Access:** Restrict database access credentials.

6.  **Database:**
    -   Run database migrations (`alembic upgrade head`) in a controlled manner during deployment.
    -   Ensure regular backups of the PostgreSQL database.

7.  **Monitoring:**
    -   Use the `/health` endpoint for load balancer health checks.
    -   Utilize `/health/detailed` for deeper system checks.
    -   Monitor Celery workers using the Flower dashboard (ensure it's appropriately secured if exposed).
    -   Set up alerts based on error logs and key performance metrics (CPU, memory, response times).
    -   Track database performance and resource usage.

## Production Logging System

The backend includes a comprehensive logging system suitable for production:

- **Structured JSON Logging**: Formatted for easy parsing by log aggregation tools.
- **Request Tracking**: Unique ID per request propagated through logs.
- **Log Segregation**: Separate files for access, errors, application, security (`access.log`, `errors.log`, `app.log`, `security.log` within `LOG_DIR`).
- **Context Awareness**: Captures user IDs, request IDs automatically.

See `backend/core/logging_config.py` for implementation details.

## Exception Handling

The backend uses global exception handling:

- HTTP exceptions (4xx, 5xx) are logged with context.
- Validation errors provide detailed information.
- Unhandled exceptions are caught and logged.
- Custom `AppException` available (`from core.exceptions import AppException`).

## Security Features

### Rate Limiting (Backend)

- Configurable request rate limits (check middleware implementation).
- Automatic temporary IP banning possible.
- Logs events to `security.log`.

### Security Headers (Backend/Proxy)

- Standard headers (CSP, X-Content-Type-Options, X-Frame-Options, HSTS, etc.) should be applied, either by the FastAPI app in production mode or preferably by a reverse proxy.

## Health Monitoring (Backend)

- `/health`: Basic check.
- `/health/database`: Database check.
- `/health/detailed`: Comprehensive check (DB, Redis, Celery, System Resources).

Ensure dependent services (Postgres, Redis, Celery workers) are running for accurate health checks.

## Language Standardization

Ensure user-facing messages and logs are standardized (typically English) for production. Utility scripts might exist in `backend/scripts` for checking/fixing.

## White-Labeling and Customization

The Rocket Launch GenAI Platform is designed with white-labeling in mind.

### Configuration

- **Environment Variables:** As detailed in [CONFIGURATION.md](CONFIGURATION.md), core settings, API keys, database connections, AI provider selection, and feature toggles are managed via environment variables.
- **Backend Settings:** `backend/core/config.py` defines the structure for settings loaded from environment variables.

### Frontend Customization

- **Theming:** Modify `frontend/tailwind.config.ts` and `frontend/src/app/globals.css` to change colors, fonts, spacing, etc.
- **Branding Assets:** Replace logo files and favicons in `frontend/public/`. Update component references.
- **Text Content:** Modify text directly within React components. Consider using an i18n library for multi-language support.

### Backend Extensibility

- **Modular Design:** Add/modify features in `backend/modules/`.
- **Service Integration:** Add new external service configurations in `core/config.py` and clients in `backend/services/`.

### Deployment

- **Docker:** Docker Compose facilitates consistent deployment. Use the `-f docker-compose.yml -f docker-compose.prod.yml` command for production builds.
- **Environment Configuration:** Use `.env.production` files for service-specific production settings, alongside the root `.env` file. 