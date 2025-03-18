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
