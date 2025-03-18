-- Create schema only
CREATE SCHEMA scare_metrics;

-- Create a test table in the public schema to verify connection works
CREATE TABLE public.test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);
