-- Script to properly create the migrations table with the migration_name column
DROP TABLE IF EXISTS migrations;

CREATE TABLE migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert records for migrations that have already been applied
INSERT INTO migrations (migration_name) VALUES 
('001_create_sm_fact_bing_ads'),
('002_create_sm_fact_google_ads'),
('003_create_campaign_mappings'),
('004_create_campaign_hierarchy'),
('005_add_network_to_bing_ads');
