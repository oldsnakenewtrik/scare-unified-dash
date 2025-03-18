-- Google Ads Schema for SCARE Unified Metrics Dashboard

-- Create the schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS scare_metrics;

-- Set the search path to use our schema
SET search_path TO scare_metrics;

-- Campaign dimension table (shared across all ad platforms)
CREATE TABLE IF NOT EXISTS scare_metrics.dim_campaign (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    external_id VARCHAR(50) NOT NULL,  -- ID from the source system
    account_id VARCHAR(50),
    account_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Google Ads fact table - based on reporting API structure
CREATE TABLE IF NOT EXISTS scare_metrics.fact_google_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    
    -- Impression metrics
    impressions BIGINT DEFAULT 0,
    impression_reach BIGINT DEFAULT 0,
    
    -- Click metrics
    clicks BIGINT DEFAULT 0,
    click_through_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Cost metrics
    cost DECIMAL(12,2) DEFAULT 0,  -- Already converted from micros
    average_cpc DECIMAL(12,2) DEFAULT 0,
    average_cpm DECIMAL(12,2) DEFAULT 0,
    
    -- Conversion metrics
    conversions DECIMAL(10,2) DEFAULT 0,
    conversion_rate DECIMAL(8,4) DEFAULT 0,
    cost_per_conversion DECIMAL(12,2) DEFAULT 0,
    conversion_value DECIMAL(12,2) DEFAULT 0,
    value_per_conversion DECIMAL(12,2) DEFAULT 0,
    
    -- Engagement metrics
    video_views BIGINT DEFAULT 0,
    view_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Quality metrics
    search_impression_share DECIMAL(8,4) DEFAULT 0,
    
    -- Status fields
    source VARCHAR(50) DEFAULT 'Google Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_google_ads_date ON scare_metrics.fact_google_ads(date);
CREATE INDEX IF NOT EXISTS idx_google_ads_campaign ON scare_metrics.fact_google_ads(campaign_id);

-- Example view for daily metrics
CREATE OR REPLACE VIEW scare_metrics.google_ads_daily_metrics AS
SELECT 
    date,
    campaign_id,
    campaign_name,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(cost) AS total_cost,
    CASE 
        WHEN SUM(impressions) > 0 THEN SUM(clicks)::DECIMAL / SUM(impressions) * 100 
        ELSE 0 
    END AS ctr,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(cost) / SUM(clicks) 
        ELSE 0 
    END AS avg_cpc,
    SUM(conversions) AS total_conversions,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(conversions)::DECIMAL / SUM(clicks) * 100 
        ELSE 0 
    END AS conversion_rate,
    CASE 
        WHEN SUM(conversions) > 0 THEN SUM(cost) / SUM(conversions) 
        ELSE 0 
    END AS cost_per_conversion
FROM 
    scare_metrics.fact_google_ads
GROUP BY 
    date, campaign_id, campaign_name
ORDER BY 
    date DESC, total_cost DESC;

-- View for campaign performance over time (monthly rollup)
CREATE OR REPLACE VIEW scare_metrics.google_ads_monthly_metrics AS
SELECT 
    DATE_TRUNC('month', date)::DATE AS month,
    campaign_id,
    campaign_name,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(cost) AS total_cost,
    CASE 
        WHEN SUM(impressions) > 0 THEN SUM(clicks)::DECIMAL / SUM(impressions) * 100 
        ELSE 0 
    END AS ctr,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(cost) / SUM(clicks) 
        ELSE 0 
    END AS avg_cpc,
    SUM(conversions) AS total_conversions,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(conversions)::DECIMAL / SUM(clicks) * 100 
        ELSE 0 
    END AS conversion_rate,
    CASE 
        WHEN SUM(conversions) > 0 THEN SUM(cost) / SUM(conversions) 
        ELSE 0 
    END AS cost_per_conversion
FROM 
    scare_metrics.fact_google_ads
GROUP BY 
    DATE_TRUNC('month', date)::DATE, campaign_id, campaign_name
ORDER BY 
    month DESC, total_cost DESC;
