-- Create the schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS scare_metrics;

-- Set the search path to use our schema
SET search_path TO scare_metrics;

-- Create dimension tables
CREATE TABLE IF NOT EXISTS scare_metrics.dim_campaign (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create fact tables for Google Ads
CREATE TABLE IF NOT EXISTS scare_metrics.fact_google_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(12,2) DEFAULT 0,
    average_cpc DECIMAL(12,2) DEFAULT 0,
    conversions DECIMAL(10,2) DEFAULT 0,
    source VARCHAR(50) DEFAULT 'Google Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create fact tables for Bing Ads
CREATE TABLE IF NOT EXISTS scare_metrics.fact_bing_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(12,2) DEFAULT 0,
    average_cpc DECIMAL(12,2) DEFAULT 0,
    conversions DECIMAL(10,2) DEFAULT 0,
    source VARCHAR(50) DEFAULT 'Bing Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create fact table for leads
CREATE TABLE IF NOT EXISTS scare_metrics.fact_leads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    leads INTEGER DEFAULT 0,
    source VARCHAR(50) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create fact table for sales
CREATE TABLE IF NOT EXISTS scare_metrics.fact_sales (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    revenue DECIMAL(12,2) DEFAULT 0,
    source VARCHAR(50) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create view that unifies metrics
CREATE OR REPLACE VIEW scare_metrics.unified_metrics_view AS
SELECT 
    c.campaign_id,
    c.campaign_name,
    c.source_system,
    g.date,
    g.impressions,
    g.clicks,
    g.cost,
    g.average_cpc AS cpc,
    g.conversions,
    COALESCE(s.revenue, 0) AS revenue
FROM scare_metrics.dim_campaign c
LEFT JOIN scare_metrics.fact_google_ads g ON c.campaign_id = g.campaign_id
LEFT JOIN scare_metrics.fact_sales s ON c.campaign_id = s.campaign_id AND g.date = s.date
WHERE c.source_system = 'Google Ads'

UNION ALL

SELECT 
    c.campaign_id,
    c.campaign_name,
    c.source_system,
    b.date,
    b.impressions,
    b.clicks,
    b.cost,
    b.average_cpc AS cpc,
    b.conversions,
    COALESCE(s.revenue, 0) AS revenue
FROM scare_metrics.dim_campaign c
LEFT JOIN scare_metrics.fact_bing_ads b ON c.campaign_id = b.campaign_id
LEFT JOIN scare_metrics.fact_sales s ON c.campaign_id = s.campaign_id AND b.date = s.date
WHERE c.source_system = 'Bing Ads';

-- Create view for unified metrics dashboard
CREATE OR REPLACE VIEW scare_metrics.view_unified_metrics AS
SELECT
    date AS full_date,
    campaign_name,
    source_system,
    impressions AS total_impressions,
    clicks AS total_clicks,
    cost AS total_cost,
    conversions AS total_conversions,
    revenue AS total_revenue,
    0 AS website_visitors,
    0 AS salesforce_leads,
    0 AS salesforce_opportunities,
    0 AS salesforce_closed_won
FROM scare_metrics.unified_metrics_view;

-- Insert some initial sample campaign data
INSERT INTO scare_metrics.dim_campaign (campaign_name, source_system, is_active)
VALUES 
    ('Summer Sale', 'Google Ads', TRUE),
    ('Brand Awareness', 'Google Ads', TRUE),
    ('Product Launch', 'Bing Ads', TRUE),
    ('Retargeting', 'Bing Ads', TRUE),
    ('Holiday Special', 'Google Ads', TRUE)
ON CONFLICT (campaign_id) DO NOTHING;
