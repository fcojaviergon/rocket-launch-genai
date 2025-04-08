# Local Installation Guide

This guide provides detailed instructions for setting up the Rocket Launch GenAI Platform locally without Docker. For most users, the [Docker Installation](DOCKER_INSTALLATION.md) method is recommended for simplicity.

## System Requirements

- 4GB+ RAM
- 10GB+ free disk space
- Administrator/sudo access (for installing dependencies)

## Prerequisites Installation

### Python 3.11+

#### macOS
```bash
# Using Homebrew
brew install python@3.12

# Verify installation
python3.12 --version
pip3.12 --version
```

#### Windows
1. Download the latest 3.12.x installer from [Python.org](https://www.python.org/downloads/)
2. Run the installer with these options:
   - ✅ Check "Add Python to PATH"
   - ✅ Check "Install pip"
   - ✅ Customize installation → Optional Features → select all
3. Verify installation:
```bash
python --version
pip --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-venv python3.12-dev python3-pip
python3.12 --version
```

### Node.js 18+ (LTS) and npm

#### macOS
```bash
# Using Homebrew
brew install node@18

# Add to PATH if needed
echo 'export PATH="/usr/local/opt/node@18/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify installation
node --version  # Should show v18.x.x
npm --version
```

#### Windows
1. Download the LTS version from [Node.js website](https://nodejs.org/)
2. Run the installer (npm is included)
3. Verify installation:
```bash
node --version  # Should show v18.x.x
npm --version
```

#### Linux (Ubuntu/Debian)
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
node --version
npm --version
```

### PostgreSQL 16+ with pgvector

#### macOS
```bash
# Using Homebrew
brew install postgresql@16
brew services start postgresql@16

# Install pgvector
brew install pgvector

# Create database and user
psql postgres
```

```sql
-- Inside psql
CREATE ROLE rocket WITH LOGIN PASSWORD 'rocket123';
ALTER ROLE rocket CREATEDB;
CREATE DATABASE rocket_launch_genai;
\c rocket_launch_genai
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL PRIVILEGES ON DATABASE rocket_launch_genai TO rocket;
\q
```

#### Windows
1. Download the installer from [PostgreSQL website](https://www.postgresql.org/download/windows/)
2. Run the installer:
   - Default port: 5432
   - Remember your superuser password
   - Complete the installation with the Stack Builder
3. Add PostgreSQL bin directory to PATH
4. Install pgvector:
   - Download and build from [pgvector GitHub](https://github.com/pgvector/pgvector), or
   - Use a pre-compiled version for Windows
5. Create database and enable extension:
```sql
psql -U postgres
CREATE ROLE rocket WITH LOGIN PASSWORD 'rocket123';
ALTER ROLE rocket CREATEDB;
CREATE DATABASE rocket_launch_genai;
\c rocket_launch_genai
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL PRIVILEGES ON DATABASE rocket_launch_genai TO rocket;
\q
```

#### Linux (Ubuntu/Debian)
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# Install PostgreSQL 16
sudo apt install postgresql-16 postgresql-server-dev-16

# Start PostgreSQL service
sudo systemctl start postgresql

# Install pgvector (build from source)
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Create database and user
sudo -u postgres psql
```

```sql
-- Inside psql
CREATE ROLE rocket WITH LOGIN PASSWORD 'rocket123';
ALTER ROLE rocket CREATEDB;
CREATE DATABASE rocket_launch_genai;
\c rocket_launch_genai
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL PRIVILEGES ON DATABASE rocket_launch_genai TO rocket;
\q
```

### Redis

#### macOS
```bash
# Using Homebrew
brew install redis
brew services start redis

# Verify installation
redis-cli ping  # Should respond with PONG
```

#### Windows
1. Download the latest MSI installer from [Redis for Windows](https://github.com/tporadowski/redis/releases)
2. Run the installer
3. Start Redis service and verify:
```bash
redis-cli ping  # Should respond with PONG
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
redis-cli ping  # Should respond with PONG
```

## Project Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rocket-launch-genai
```

### 2. Backend Setup

1. Create and activate Python virtual environment:
```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Set up environment variables:
For local installations, create `.env.local` files in both the `backend` and `frontend` directories (you can copy from the `.env.development` files).
Configure the necessary variables as described in the central [CONFIGURATION.md](../CONFIGURATION.md) guide.
**Key differences for local setup:**
  - Database/Redis URLs should use `localhost`.
  - `INTERNAL_BACKEND_URL` is not typically needed for the frontend.
  - Ensure ports don't conflict with other local services.

4. Initialize database:
```bash
alembic upgrade head
```

5. Start the backend development server:
```bash
python run.py
```

The API should now be running at http://localhost:8000 with documentation at http://localhost:8000/docs.

### 3. Frontend Setup

In a new terminal:

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
Create `frontend/.env.local` (e.g., by copying `frontend/.env.development`).
Configure the necessary variables as described in the central [CONFIGURATION.md](../CONFIGURATION.md) guide, ensuring `NEXTAUTH_URL` and `NEXT_PUBLIC_BACKEND_URL` point to your local setup (e.g., `http://localhost:3000` and `http://localhost:8000`).

4. Start the development server:
```bash
npm run dev
```

The frontend should now be running at http://localhost:3000.

### 4. Celery Workers (Optional)

In a new terminal:

1. Activate the backend virtual environment:
```bash
cd backend
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Start Celery worker:
```bash
bash start_worker.sh
```

## Running the Application

After completing the setup, you can access:

- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555) (if Celery is running)

Default admin login:
- Email: admin@example.com
- Password: password (as set in backend/.env.local)

## Development Workflow

- Backend changes are automatically reloaded in development mode
- Frontend changes use Next.js hot reloading
- Database migrations: `alembic revision --autogenerate -m "description"` then `alembic upgrade head`

## Environment Variables Reference

See the central [CONFIGURATION.md](../CONFIGURATION.md) guide for a complete reference of all environment variables.

## Troubleshooting

### Database Connection Issues

1. Check if PostgreSQL is running:
```bash
# macOS
brew services list | grep postgresql

# Windows
sc query postgresql

# Linux
sudo systemctl status postgresql
```

2. Test database connection:
```bash
psql -U rocket -d rocket_launch_genai -h localhost
```

3. Verify pgvector installation:
```bash
psql -U postgres -d rocket_launch_genai -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Python/Node.js Issues

1. Verify correct Python version:
```bash
python --version  # Should be 3.12+
```

2. Reinstall dependencies:
```bash
# Backend
pip install --upgrade pip
pip install -r requirements.txt

# Frontend
rm -rf node_modules
npm cache clean --force
npm install
```

### Port Conflicts

If ports are already in use:

1. Check for services using the required ports:
```bash
# macOS/Linux
lsof -i :3000
lsof -i :8000

# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

2. Modify the ports:
   - Backend: Edit `run.py` to change the port
   - Frontend: Edit `package.json` scripts to include a different port

Note: Server execution is managed by the project owner. Once installation is complete, notify them to refresh the servers. 