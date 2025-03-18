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

-- Create fact table for Matomo analytics
CREATE TABLE IF NOT EXISTS scare_metrics.fact_matomo (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT,
    campaign_name VARCHAR(255),
    visitors INTEGER DEFAULT 0,
    page_views INTEGER DEFAULT 0,
    bounce_rate DECIMAL(5,2) DEFAULT 0,
    avg_time_on_site DECIMAL(10,2) DEFAULT 0,
    goals_completed INTEGER DEFAULT 0,
    source VARCHAR(50) DEFAULT 'Matomo',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create fact table for RedTrack data
CREATE TABLE IF NOT EXISTS scare_metrics.fact_redtrack (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT,
    campaign_name VARCHAR(255),
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    revenue DECIMAL(12,2) DEFAULT 0,
    cost DECIMAL(12,2) DEFAULT 0,
    profit DECIMAL(12,2) DEFAULT 0,
    roi DECIMAL(8,2) DEFAULT 0,
    source VARCHAR(50) DEFAULT 'RedTrack',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create unified view that combines metrics from all sources
CREATE OR REPLACE VIEW scare_metrics.unified_metrics_view AS
-- Google Ads data
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
    0 AS revenue,
    0 AS visitors,
    0 AS page_views,
    0 AS bounce_rate,
    0 AS avg_time_on_site,
    0 AS roi
FROM scare_metrics.dim_campaign c
JOIN scare_metrics.fact_google_ads g ON c.campaign_id = g.campaign_id
WHERE c.source_system = 'Google Ads'

UNION ALL

-- Bing Ads data
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
    0 AS revenue,
    0 AS visitors,
    0 AS page_views,
    0 AS bounce_rate,
    0 AS avg_time_on_site,
    0 AS roi
FROM scare_metrics.dim_campaign c
JOIN scare_metrics.fact_bing_ads b ON c.campaign_id = b.campaign_id
WHERE c.source_system = 'Bing Ads'

UNION ALL

-- Matomo data
SELECT 
    c.campaign_id,
    c.campaign_name,
    c.source_system,
    m.date,
    0 AS impressions,
    0 AS clicks,
    0 AS cost,
    0 AS cpc,
    m.goals_completed AS conversions,
    0 AS revenue,
    m.visitors,
    m.page_views,
    m.bounce_rate,
    m.avg_time_on_site,
    0 AS roi
FROM scare_metrics.dim_campaign c
JOIN scare_metrics.fact_matomo m ON c.campaign_id = m.campaign_id
WHERE c.source_system = 'Matomo'

UNION ALL

-- RedTrack data
SELECT 
    c.campaign_id,
    c.campaign_name,
    c.source_system,
    r.date,
    0 AS impressions,
    r.clicks,
    r.cost,
    CASE WHEN r.clicks > 0 THEN r.cost / r.clicks ELSE 0 END AS cpc,
    r.conversions,
    r.revenue,
    0 AS visitors,
    0 AS page_views,
    0 AS bounce_rate,
    0 AS avg_time_on_site,
    r.roi
FROM scare_metrics.dim_campaign c
JOIN scare_metrics.fact_redtrack r ON c.campaign_id = r.campaign_id
WHERE c.source_system = 'RedTrack';

-- Create view for dashboard with aggregated metrics
CREATE OR REPLACE VIEW scare_metrics.view_unified_metrics AS
SELECT
    date AS full_date,
    campaign_name,
    source_system,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(cost) AS total_cost,
    SUM(conversions) AS total_conversions,
    SUM(revenue) AS total_revenue,
    SUM(visitors) AS website_visitors,
    SUM(goals_completed) AS salesforce_leads,
    0 AS salesforce_opportunities,
    0 AS salesforce_closed_won
FROM (
    -- Google Ads data
    SELECT 
        g.date,
        c.campaign_name,
        c.source_system,
        g.impressions,
        g.clicks,
        g.cost,
        g.conversions,
        0 AS revenue,
        0 AS visitors,
        0 AS goals_completed
    FROM scare_metrics.dim_campaign c
    JOIN scare_metrics.fact_google_ads g ON c.campaign_id = g.campaign_id
    WHERE c.source_system = 'Google Ads'

    UNION ALL

    -- Bing Ads data
    SELECT 
        b.date,
        c.campaign_name,
        c.source_system,
        b.impressions,
        b.clicks,
        b.cost,
        b.conversions,
        0 AS revenue,
        0 AS visitors,
        0 AS goals_completed
    FROM scare_metrics.dim_campaign c
    JOIN scare_metrics.fact_bing_ads b ON c.campaign_id = b.campaign_id
    WHERE c.source_system = 'Bing Ads'

    UNION ALL

    -- Matomo data
    SELECT 
        m.date,
        c.campaign_name,
        c.source_system,
        0 AS impressions,
        0 AS clicks,
        0 AS cost,
        m.goals_completed AS conversions,
        0 AS revenue,
        m.visitors,
        m.goals_completed
    FROM scare_metrics.dim_campaign c
    JOIN scare_metrics.fact_matomo m ON c.campaign_id = m.campaign_id
    WHERE c.source_system = 'Matomo'

    UNION ALL

    -- RedTrack data
    SELECT 
        r.date,
        c.campaign_name,
        c.source_system,
        0 AS impressions,
        r.clicks,
        r.cost,
        r.conversions,
        r.revenue,
        0 AS visitors,
        0 AS goals_completed
    FROM scare_metrics.dim_campaign c
    JOIN scare_metrics.fact_redtrack r ON c.campaign_id = r.campaign_id
    WHERE c.source_system = 'RedTrack'
) AS combined_data
GROUP BY full_date, campaign_name, source_system;

-- Insert sample campaign data
INSERT INTO scare_metrics.dim_campaign (campaign_id, campaign_name, source_system, is_active)
VALUES 
    (1, 'Summer Sale', 'Google Ads', TRUE),
    (2, 'Brand Awareness', 'Google Ads', TRUE),
    (3, 'Product Launch', 'Bing Ads', TRUE),
    (4, 'Retargeting', 'Bing Ads', TRUE),
    (5, 'Holiday Special', 'Google Ads', TRUE),
    (6, 'Website Traffic', 'Matomo', TRUE),
    (7, 'Conversion Tracking', 'RedTrack', TRUE),
    (8, 'Lead Generation', 'RedTrack', TRUE)
ON CONFLICT (campaign_id) DO NOTHING;

-- Sample data for Google Ads
INSERT INTO scare_metrics.fact_google_ads (date, campaign_id, campaign_name, account_id, account_name, impressions, clicks, cost, average_cpc, conversions)
VALUES
    ('2025-03-01', 1, 'Summer Sale', '123456789', 'Main Account', 12500, 750, 1250.50, 1.67, 25),
    ('2025-03-02', 1, 'Summer Sale', '123456789', 'Main Account', 13200, 810, 1350.80, 1.67, 32),
    ('2025-03-03', 1, 'Summer Sale', '123456789', 'Main Account', 14100, 920, 1480.20, 1.61, 38),
    ('2025-03-01', 2, 'Brand Awareness', '123456789', 'Main Account', 25000, 1250, 2100.30, 1.68, 15),
    ('2025-03-02', 2, 'Brand Awareness', '123456789', 'Main Account', 27000, 1320, 2250.40, 1.70, 18),
    ('2025-03-03', 2, 'Brand Awareness', '123456789', 'Main Account', 26500, 1280, 2150.20, 1.68, 22),
    ('2025-03-01', 5, 'Holiday Special', '123456789', 'Main Account', 18000, 950, 1600.75, 1.69, 45),
    ('2025-03-02', 5, 'Holiday Special', '123456789', 'Main Account', 19200, 980, 1700.20, 1.73, 52),
    ('2025-03-03', 5, 'Holiday Special', '123456789', 'Main Account', 20500, 1050, 1850.30, 1.76, 58);

-- Sample data for Bing Ads
INSERT INTO scare_metrics.fact_bing_ads (date, campaign_id, campaign_name, account_id, account_name, impressions, clicks, cost, average_cpc, conversions)
VALUES
    ('2025-03-01', 3, 'Product Launch', 'BIN12345', 'Bing Main', 8500, 420, 650.25, 1.55, 12),
    ('2025-03-02', 3, 'Product Launch', 'BIN12345', 'Bing Main', 9200, 450, 680.50, 1.51, 15),
    ('2025-03-03', 3, 'Product Launch', 'BIN12345', 'Bing Main', 9800, 490, 720.30, 1.47, 18),
    ('2025-03-01', 4, 'Retargeting', 'BIN12345', 'Bing Main', 5200, 380, 520.80, 1.37, 25),
    ('2025-03-02', 4, 'Retargeting', 'BIN12345', 'Bing Main', 5500, 410, 550.40, 1.34, 28),
    ('2025-03-03', 4, 'Retargeting', 'BIN12345', 'Bing Main', 5900, 450, 590.25, 1.31, 32);

-- Sample data for Matomo
INSERT INTO scare_metrics.fact_matomo (date, campaign_id, campaign_name, visitors, page_views, bounce_rate, avg_time_on_site, goals_completed)
VALUES
    ('2025-03-01', 6, 'Website Traffic', 3500, 12000, 42.5, 125.8, 85),
    ('2025-03-02', 6, 'Website Traffic', 3800, 13500, 40.2, 130.5, 95),
    ('2025-03-03', 6, 'Website Traffic', 4200, 14800, 38.7, 142.3, 105),
    ('2025-03-01', 1, 'Summer Sale', 1200, 4500, 45.8, 118.2, 35),
    ('2025-03-02', 1, 'Summer Sale', 1350, 5000, 43.2, 122.5, 42),
    ('2025-03-03', 1, 'Summer Sale', 1500, 5600, 41.5, 128.7, 48);

-- Sample data for RedTrack
INSERT INTO scare_metrics.fact_redtrack (date, campaign_id, campaign_name, clicks, conversions, revenue, cost, profit, roi)
VALUES
    ('2025-03-01', 7, 'Conversion Tracking', 850, 42, 2100.00, 950.25, 1149.75, 121.0),
    ('2025-03-02', 7, 'Conversion Tracking', 920, 48, 2400.00, 1050.50, 1349.50, 128.5),
    ('2025-03-03', 7, 'Conversion Tracking', 980, 52, 2600.00, 1100.75, 1499.25, 136.2),
    ('2025-03-01', 8, 'Lead Generation', 1250, 85, 4250.00, 1850.30, 2399.70, 129.7),
    ('2025-03-02', 8, 'Lead Generation', 1320, 92, 4600.00, 1950.80, 2649.20, 135.8),
    ('2025-03-03', 8, 'Lead Generation', 1450, 98, 4900.00, 2050.25, 2849.75, 139.0);
