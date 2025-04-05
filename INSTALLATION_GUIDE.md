# Rocket Launch GenAI Platform - Installation Guide

This guide provides instructions for setting up the Rocket Launch GenAI Platform for development or production using Docker Compose.

## Prerequisites

- **Git:** To clone the repository.
- **Docker:** Version 20.10 or later. [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose:** Version v2.10 or later (usually included with Docker Desktop). [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Text Editor/IDE:** For editing configuration files (e.g., VS Code).
- **Web Browser:** For accessing the frontend application and API docs.
- **(Optional) OpenAI API Key:** If you plan to use OpenAI models for completions, chat, or embeddings.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url> rocket-launch-genai
    cd rocket-launch-genai
    ```

2.  **Configure Environment Variables:**
    The platform uses environment variables for configuration. A central `.env` file in the root directory is used by Docker Compose to inject variables into the different services (frontend, backend, database, etc.).

    -   **Create the main `.env` file:**
        Copy the example file:
        ```bash
        cp .env.example .env
        ```
    -   **Edit `.env`:**
        Open the `.env` file in your text editor and configure the following variables:

        **Database (PostgreSQL):**
        - `POSTGRES_DB`: Name of the database to create.
        - `POSTGRES_USER`: Username for the database.
        - `POSTGRES_PASSWORD`: Password for the database user. **Choose a strong password.**

        **Backend (FastAPI):**
        - `SECRET_KEY`: A strong secret key for JWT token signing. Generate one using: `openssl rand -hex 32`
        - `ACCESS_TOKEN_EXPIRE_MINUTES`: Validity period for access tokens (e.g., `30`).
        - `SUPERUSER_EMAIL`: Email for the initial administrator account.
        - `SUPERUSER_PASSWORD`: Password for the initial administrator account. **Choose a strong password.**
        - `DATABASE_URL`: *Leave this as is* if using the default Docker Compose setup (`postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}`). It references the service name (`db`) within the Docker network.
        - `REDIS_URL`: *Leave this as is* if using the default Docker Compose setup (`redis://redis:6379/0`). It references the service name (`redis`).
        - `OPENAI_API_KEY`: (Optional) Your OpenAI API key if you intend to use OpenAI features.
        - `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames for the backend API (e.g., `localhost,yourdomain.com`). Defaults to `*` if not set (less secure).

        **Frontend (Next.js):**
        - `NEXTAUTH_URL`: The full URL where the frontend will be accessible (e.g., `http://localhost:3000`). This is crucial for NextAuth redirects.
        - `NEXTAUTH_SECRET`: A strong secret key for NextAuth session encryption. Generate one using: `openssl rand -base64 32`
        - `NEXT_PUBLIC_API_BASE_URL`: The full URL where the backend API will be accessible *from the user's browser* (e.g., `http://localhost:8000`).

        **Other:**
        - `COMPOSE_PROJECT_NAME`: (Optional) A name for your Docker Compose project (e.g., `ai_rocket`).
        - `TZ`: Timezone (e.g., `UTC`, `America/New_York`).

    -   **(Optional) Production vs. Development Overrides:**
        The `docker-compose.yml` might be set up to use override files like `docker-compose.prod.yml` or check for `.env.production`. Review the `docker-compose.yml` file for specifics on how environment-specific settings are handled.
        You might need to create `.env.production` or `.env.development` based on the `docker-compose.yml` logic if you need different settings per environment.

3.  **Build and Start Containers:**
    Open your terminal in the root directory (`rocket-launch-genai`) where the `docker-compose.yml` file is located.

    -   **For Development (typically includes hot-reloading):**
        ```bash
        docker-compose up --build
        ```
        The `--build` flag ensures images are rebuilt if Dockerfiles or context change. You can omit it for subsequent starts if no code affecting the image has changed.

    -   **For Production (usually runs optimized builds, detached):**
        (Check if a specific production compose file exists, e.g., `docker-compose.prod.yml`)
        ```bash
        # Example if using an override file:
        # docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

        # If no specific prod file, just run detached:
        docker-compose up --build -d
        ```
        The `-d` flag runs the containers in detached mode (in the background).

4.  **Database Migrations (First Time Setup):**
    After the containers are running (especially the `db` and `backend` services), you need to apply the initial database schema migrations.

    -   Find the name of your running backend container:
        ```bash
        docker-compose ps
        ```
        Look for the service named `backend` or similar.
    -   Execute the Alembic migration command inside the backend container:
        ```bash
        docker-compose exec backend alembic upgrade head
        ```
        *Note: Some setups might run migrations automatically via the `docker-entrypoint.sh` script inside the backend container. Check the `Dockerfile` and `docker-entrypoint.sh` for the `backend` service.* If it runs automatically, you can skip this step.

5.  **Access the Application:**

    -   **Frontend:** Open your web browser and navigate to the `NEXTAUTH_URL` you configured (e.g., `http://localhost:3000`).
    -   **Backend API Docs:** Navigate to `NEXT_PUBLIC_API_BASE_URL` + `/docs` (e.g., `http://localhost:8000/docs`).
    -   **(Optional) Flower Dashboard:** If the `flower` service is running, access it typically at `http://localhost:5555`.

6.  **Initial Login:**
    Use the `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD` configured in the `.env` file to log in to the frontend application for the first time.

## Stopping the Application

-   **If running in the foreground (no `-d` flag):** Press `Ctrl+C` in the terminal where `docker-compose up` is running.
-   **If running in detached mode (`-d` flag):**
    ```bash
    docker-compose down
    ```
    To stop and remove volumes (like the database data, **use with caution**):
    ```bash
    docker-compose down -v
    ```

## Troubleshooting

-   **Port Conflicts:** Ensure the ports defined in `docker-compose.yml` (e.g., 3000, 8000, 5432, 6379) are not already in use on your host machine.
-   **Container Logs:** Check logs for specific services:
    ```bash
    docker-compose logs -f <service_name> # e.g., docker-compose logs -f backend
    ```
-   **`.env` File:** Double-check that the `.env` file is in the root directory and has the correct variables set. Ensure there are no trailing spaces or incorrect syntax.
-   **Docker Resources:** Ensure Docker has sufficient memory and CPU resources allocated, especially for the database and AI processing.
-   **Database Connection:** Verify the `DATABASE_URL` in the backend's environment is correct and the `db` container is running and healthy.
-   **Permissions:** On Linux, you might encounter permissions issues with mounted volumes. Ensure the user running Docker has the necessary permissions. 