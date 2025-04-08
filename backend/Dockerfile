FROM python:3.11-slim

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "Docker image user" appuser

WORKDIR /app

# Install system dependencies including gosu
RUN apt-get update
RUN apt-get install -y -qq --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-traditional \
    gosu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Now copy the rest of the application code
COPY --chown=appuser:appuser . .

# Copy entrypoint (already included in the code copy above, ensure permissions)
RUN chmod +x docker-entrypoint.sh

# Create storage directory (owner will be fixed by entrypoint)
RUN mkdir -p storage/documents

# Change ownership of the app directory so appuser can potentially write logs etc.
# Note: storage/documents ownership is handled by entrypoint due to volume mount.
RUN chown -R appuser:appuser /app

# Expose ports
EXPOSE 8000

# Switch back to root USER to ensure entrypoint runs as root
USER root

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (will be run as appuser via su-exec in entrypoint)
CMD ["python", "run.py"] 