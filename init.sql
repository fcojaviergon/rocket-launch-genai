-- Create the role only if it doesn't exist
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'rocket') THEN
      CREATE ROLE rocket WITH LOGIN PASSWORD 'rocket123';
   END IF;
END
$$;

ALTER ROLE rocket CREATEDB;

-- Create the database only if it doesn't exist
SELECT 'CREATE DATABASE rocket_launch_genai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rocket_launch_genai')\gexec

-- Connect to the database
\c rocket_launch_genai

-- Grant usage and create on the public schema explicitly
GRANT USAGE, CREATE ON SCHEMA public TO rocket;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant privileges (safe to run multiple times)
GRANT ALL PRIVILEGES ON DATABASE rocket_launch_genai TO rocket;
GRANT ALL ON SCHEMA public TO rocket; -- Grant privileges on the public schema
GRANT ALL ON ALL TABLES IN SCHEMA public TO rocket; -- Grant on existing tables
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO rocket; -- Grant on existing sequences

-- Optional: Ensure future objects are also granted
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO rocket;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO rocket;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO rocket; -- Add for functions/procedures if needed
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TYPES TO rocket; -- Add for types 