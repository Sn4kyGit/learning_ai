-- Initialize database for Local Business Intelligence Bot

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance
-- These will be created by Alembic migrations, but we can prepare the database

-- Set timezone
SET timezone = 'UTC';

-- Create a test database for running tests
CREATE DATABASE businessbot_test;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE businessbot TO businessbot;
GRANT ALL PRIVILEGES ON DATABASE businessbot_test TO businessbot;