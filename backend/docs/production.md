# Production Deployment Guide

This guide outlines the required steps and considerations for deploying the Rocket Launch GenAI Platform to production environments.

## Logging System

The platform includes a comprehensive logging system designed for production environments:

### Features

- **Structured JSON Logging**: In production, logs are formatted as JSON for easy parsing by log aggregation tools like ELK, Datadog, or Graylog.
- **Request Tracking**: Each request receives a unique ID that is propagated throughout the logs for better traceability.
- **Log Segregation**: Logs are separated into different files:
  - `access.log`: HTTP request/response information
  - `errors.log`: Error-level logs
  - `app.log`: General application logs
  - `security.log`: Authentication and security-related events
- **Context Awareness**: Logs automatically capture contextual information like user IDs and request IDs.
- **Environment-Based Configuration**: Different log formats and levels for development vs. production environments.

### Using the Logging System

```python
from core.logging_config import get_logger

# Get a logger with the current module name
logger = get_logger(__name__)

# Basic logging
logger.info("This is an informational message")
logger.error("An error occurred", exc_info=True)

# Logging with context
logger.warning("Security alert", extra={"user_id": "123", "action": "login_failed"})

# For request-specific logging
request_id = request.state.request_id  # From RequestLoggingMiddleware
user_id = current_user.id if current_user else None
logger = get_logger(__name__, request_id=request_id, user_id=user_id)
```

### Converting Print Statements to Logs

The project includes a utility for finding and converting print statements to proper logging:

```bash
# Find all print statements without changing them
python -c "from core.print_to_log import bulk_convert_prints; bulk_convert_prints('./backend', dry_run=True)"

# Convert print statements to logger calls
python -c "from core.print_to_log import bulk_convert_prints; bulk_convert_prints('./backend', dry_run=False)"
```

## Exception Handling

The platform includes a global exception handling system:

- HTTP exceptions (4xx) are properly logged with context
- Validation errors are logged with detailed information
- Unhandled exceptions are caught, logged, and return appropriate responses
- Custom `AppException` class for application-specific errors

Usage example:

```python
from core.exceptions import AppException

# In a route handler
if not valid_data:
    # This will be properly caught and logged
    raise AppException(status_code=400, detail="Invalid data format")
```

## Language Standardization

For production readiness, ensure all user-facing messages follow these guidelines:

- Use English for all error messages and logs
- Standard error format: `f"Error <action>: {error_details}"`
- Avoid debug information in user-facing errors

## Production Checklist

Before deploying to production:

1. **Environment Variables**:
   - Ensure all secrets are set via environment variables or secure vault
   - Verify `ENVIRONMENT=production` is set

2. **Logging**:
   - Verify log directory permissions (`backend/logs/`)
   - Configure log rotation via OS (in addition to application-level rotation)
   - Set up log forwarding to centralized logging system if applicable

3. **Error Handling**:
   - Verify custom exception handlers are working
   - Ensure no tracebacks are exposed to end users

4. **Performance**:
   - Adjust worker counts in `start_worker.sh` based on server capacity
   - Configure appropriate connection pool sizes

5. **Security**:
   - Enable HTTPS
   - Verify CORS settings
   - Ensure proper rate limiting is in place

## Monitoring

For production monitoring:

1. Use the `/health` endpoint for basic availability checks
2. Set up alerts on error logs
3. Monitor worker processes via Flower (`start_flower.sh`)
4. Track database performance via logs 

## Security Features

The platform includes several security features for production environments:

### Rate Limiting

The `SecurityMiddleware` provides protection against abuse:

- Configurable request rate limits (defaults to 60 requests per minute in production)
- Automatic temporary IP banning for abuse
- Excludes local/development IPs from rate limiting
- Logs all rate limit events to the security log

### Security Headers

In production mode, the application automatically adds security headers to all responses:

- Content-Security-Policy: Protects against XSS attacks
- X-Content-Type-Options: Prevents MIME type sniffing
- X-Frame-Options: Prevents clickjacking
- X-XSS-Protection: Additional XSS protection
- Strict-Transport-Security: Forces HTTPS connections
- Permissions-Policy: Restricts browser features

## Health Monitoring

The platform includes comprehensive health monitoring endpoints:

- `/health`: Basic health check (for load balancers)
- `/health/database`: Database-specific health check
- `/health/detailed`: Comprehensive system health check including:
  - Database connection and pool statistics
  - Redis connection status
  - Celery worker status
  - System resource usage (CPU, memory, disk)

Example usage:

```bash
# Basic health check
curl http://localhost:8000/health

# Comprehensive health check
curl http://localhost:8000/health/detailed
```

### Starting Required Services for Health Checks

For the health check to report all systems as healthy, ensure these services are running:

1. **Database**: PostgreSQL must be running and accessible
   ```bash
   # Check if PostgreSQL is running
   pg_isready -h localhost
   ```

2. **Redis**: Redis server must be running
   ```bash
   # Check if Redis is running
   redis-cli ping
   ```

3. **Celery Workers**: Start Celery workers using the provided script
   ```bash
   cd backend
   # Start Celery workers
   ./start_worker.sh
   ```

If any of these services aren't running, the corresponding health check will report "unhealthy" status.

## Language Standardization

To ensure consistent, professional error messages in production, use the included language standardization tool:

```bash
# Find Spanish strings in the codebase (dry run)
python -m backend.scripts.i18n_fixer --directory ./backend --dry-run

# Fix Spanish strings in the codebase
python -m backend.scripts.i18n_fixer --directory ./backend
```

This will convert Spanish error messages to standardized English messages, improving user experience in production. 