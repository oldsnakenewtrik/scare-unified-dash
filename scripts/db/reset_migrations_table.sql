-- Script to reset the migrations table
-- Run this in the Railway PostgreSQL console

-- Drop the existing migrations table that might have wrong schema
DROP TABLE IF EXISTS migrations;

-- The application will recreate it with the correct schema on startup
