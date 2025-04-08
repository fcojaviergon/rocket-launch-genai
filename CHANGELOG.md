# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Environment Variables**: Updated and standardized environment variable names across backend, frontend, and Docker configurations.
    - Renamed `SUPERUSER_EMAIL` to `INITIAL_ADMIN_EMAIL`.
    - Renamed `SUPERUSER_PASSWORD` to `INITIAL_ADMIN_PASSWORD`.
    - Renamed `ALGORITHM` (backend JWT) to `JWT_ALGORITHM`.
    - Standardized on `NEXT_PUBLIC_BACKEND_URL` for frontend access to the backend base URL.
    - Added `INTERNAL_BACKEND_URL` for server-side communication within Docker.
    - Added specific Celery configuration variables (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_WORKER_CONCURRENCY`, `CELERY_WORKER_POOL`).
    - Added AI provider configuration (`AI_PROVIDER`, `ANTHROPIC_API_KEY`) and default model selection (`DEFAULT_CHAT_MODEL`, `DEFAULT_EMBEDDING_MODEL`).
    - Added JWT refresh token configuration (`REFRESH_TOKEN_EXPIRE_DAYS`).
    - Added logging configuration (`LOG_LEVEL`, `LOG_DIR`).
    - Added environment indicators (`ENVIRONMENT`, `NODE_ENV`).
    - Added frontend API specifics (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_VERSION`).
    - Added optional frontend token expiry hint (`NEXT_PUBLIC_ACCESS_TOKEN_EXPIRE_MINUTES`).
    - Updated documentation (`LOCAL_INSTALLATION.md`, `INSTALLATION_GUIDE.md`, `DOCKER_INSTALLATION.md`, `FUNCTIONAL_TECH_SSF.md`) to reflect these changes and clarify usage, especially regarding Docker environments.
- **Documentation**: Reorganized documentation into a central `docs/` directory.
    - Created `docs/CONFIGURATION.md` as the single source of truth for environment variables.
    - Split `FUNCTIONAL_TECH_SSF.md` into `docs/OVERVIEW.md` and `docs/ARCHITECTURE.md`.
    - Merged `PRODUCTION_RECOMMENDATION.md` content into `docs/DEPLOYMENT.md`.
    - Updated installation guides (`docs/DOCKER_INSTALLATION.md`, `docs/LOCAL_INSTALLATION.md`) and READMEs (`README.md`, `backend/README.md`, `frontend/README.md`) to link to the new centralized documentation files.

### Fixed
- N/A (Related to this specific set of changes)

### Added
- `CHANGELOG.md` file to track project changes.

### Removed
- Redundant `INSTALLATION_GUIDE.md`. Merged essential content into `DOCKER_INSTALLATION.md`.
- `FUNCTIONAL_TECH_SSF.md` (split into `OVERVIEW.md` and `ARCHITECTURE.md`).
- `PRODUCTION_RECOMMENDATION.md` (merged into `DEPLOYMENT.md`). 