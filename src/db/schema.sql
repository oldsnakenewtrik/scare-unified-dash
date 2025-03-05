-- Database schema for SCARE Unified Metrics Dashboard

-- Create schema
CREATE SCHEMA IF NOT EXISTS scare_metrics;

-- Set search path
SET search_path TO scare_metrics, public;

-- Common dimension tables

-- Date dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_id SERIAL PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_of_week INT NOT NULL,
    day_name VARCHAR(10) NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- Campaign dimension
CREATE TABLE IF NOT EXISTS dim_campaign (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    source_campaign_id VARCHAR(255),
    created_date DATE NOT NULL,
    updated_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(source_system, source_campaign_id)
);

-- Ad Group dimension
CREATE TABLE IF NOT EXISTS dim_ad_group (
    ad_group_id SERIAL PRIMARY KEY,
    campaign_id INT REFERENCES dim_campaign(campaign_id),
    ad_group_name VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    source_ad_group_id VARCHAR(255),
    created_date DATE NOT NULL,
    updated_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(source_system, source_ad_group_id)
);

-- Fact tables for each data source

-- RedTrack Metrics
CREATE TABLE IF NOT EXISTS fact_redtrack (
    redtrack_id SERIAL PRIMARY KEY,
    date_id INT REFERENCES dim_date(date_id),
    campaign_id INT REFERENCES dim_campaign(campaign_id),
    clicks INT NOT NULL DEFAULT 0,
    impressions INT NOT NULL DEFAULT 0,
    conversions INT NOT NULL DEFAULT 0,
    revenue DECIMAL(15, 2) NOT NULL DEFAULT 0,
    cost DECIMAL(15, 2) NOT NULL DEFAULT 0,
    roi DECIMAL(10, 2),
    ctr DECIMAL(10, 4),
    epc DECIMAL(10, 4),
    cpc DECIMAL(10, 4),
    source_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Matomo Metrics
CREATE TABLE IF NOT EXISTS fact_matomo (
    matomo_id SERIAL PRIMARY KEY,
    date_id INT REFERENCES dim_date(date_id),
    campaign_id INT REFERENCES dim_campaign(campaign_id),
    visitors INT NOT NULL DEFAULT 0,
    unique_visitors INT NOT NULL DEFAULT 0,
    page_views INT NOT NULL DEFAULT 0,
    bounce_rate DECIMAL(10, 2),
    avg_time_on_site DECIMAL(10, 2),
    goal_conversions INT NOT NULL DEFAULT 0,
    source_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Google Ads Metrics
CREATE TABLE IF NOT EXISTS fact_google_ads (
    google_ads_id SERIAL PRIMARY KEY,
    date_id INT REFERENCES dim_date(date_id),
    campaign_id INT REFERENCES dim_campaign(campaign_id),
    ad_group_id INT REFERENCES dim_ad_group(ad_group_id),
    impressions INT NOT NULL DEFAULT 0,
    clicks INT NOT NULL DEFAULT 0,
    cost DECIMAL(15, 2) NOT NULL DEFAULT 0,
    conversions DECIMAL(10, 2) NOT NULL DEFAULT 0,
    conversion_value DECIMAL(15, 2) NOT NULL DEFAULT 0,
    ctr DECIMAL(10, 4),
    cpc DECIMAL(10, 4),
    conversion_rate DECIMAL(10, 4),
    cost_per_conversion DECIMAL(15, 2),
    average_position DECIMAL(10, 2),
    source_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Bing Ads Metrics
CREATE TABLE IF NOT EXISTS fact_bing_ads (
    bing_ads_id SERIAL PRIMARY KEY,
    date_id INT REFERENCES dim_date(date_id),
    campaign_id INT REFERENCES dim_campaign(campaign_id),
    ad_group_id INT REFERENCES dim_ad_group(ad_group_id),
    impressions INT NOT NULL DEFAULT 0,
    clicks INT NOT NULL DEFAULT 0,
    cost DECIMAL(15, 2) NOT NULL DEFAULT 0,
    conversions DECIMAL(10, 2) NOT NULL DEFAULT 0,
    conversion_value DECIMAL(15, 2) NOT NULL DEFAULT 0,
    ctr DECIMAL(10, 4),
    cpc DECIMAL(10, 4),
    conversion_rate DECIMAL(10, 4),
    cost_per_conversion DECIMAL(15, 2),
    average_position DECIMAL(10, 2),
    source_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Salesforce Metrics
CREATE TABLE IF NOT EXISTS fact_salesforce (
    salesforce_id SERIAL PRIMARY KEY,
    date_id INT REFERENCES dim_date(date_id),
    campaign_id INT REFERENCES dim_campaign(campaign_id),
    leads INT NOT NULL DEFAULT 0,
    qualified_leads INT NOT NULL DEFAULT 0, 
    opportunities INT NOT NULL DEFAULT 0,
    closed_won INT NOT NULL DEFAULT 0,
    closed_lost INT NOT NULL DEFAULT 0,
    revenue DECIMAL(15, 2) NOT NULL DEFAULT 0,
    source_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Leads fact table for tracking smooth leads by campaign
CREATE TABLE IF NOT EXISTS fact_leads (
    lead_id SERIAL PRIMARY KEY,
    date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    campaign_id INTEGER NOT NULL REFERENCES dim_campaign(campaign_id),
    leads INTEGER NOT NULL DEFAULT 0,
    lead_source VARCHAR(50),
    lead_type VARCHAR(50),
    lead_quality_score DECIMAL(5, 2),
    is_qualified BOOLEAN DEFAULT FALSE,
    source_data JSONB,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Sales fact table for tracking sales data
CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id SERIAL PRIMARY KEY,
    date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    campaign_id INTEGER NOT NULL REFERENCES dim_campaign(campaign_id),
    sale_amount DECIMAL(12, 2) NOT NULL,
    sale_type VARCHAR(50), -- e.g., 'M', 'T', 'D'
    sale_source VARCHAR(50), -- e.g., 'ONL', 'OFL'
    customer_id VARCHAR(100),
    order_id VARCHAR(100),
    source_data JSONB,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Unified metrics view (aggregated)
CREATE OR REPLACE VIEW view_unified_metrics AS
SELECT 
    d.full_date,
    c.campaign_name,
    c.source_system,
    COALESCE(rt.clicks, 0) + COALESCE(ga.clicks, 0) + COALESCE(ba.clicks, 0) AS total_clicks,
    COALESCE(rt.impressions, 0) + COALESCE(ga.impressions, 0) + COALESCE(ba.impressions, 0) AS total_impressions,
    COALESCE(rt.cost, 0) + COALESCE(ga.cost, 0) + COALESCE(ba.cost, 0) AS total_cost,
    COALESCE(rt.conversions, 0) + COALESCE(ga.conversions, 0) + COALESCE(ba.conversions, 0) AS total_conversions,
    COALESCE(rt.revenue, 0) + COALESCE(ga.conversion_value, 0) + COALESCE(ba.conversion_value, 0) + COALESCE(sf.revenue, 0) AS total_revenue,
    COALESCE(m.visitors, 0) AS website_visitors,
    COALESCE(m.unique_visitors, 0) AS unique_visitors,
    COALESCE(m.bounce_rate, 0) AS bounce_rate,
    COALESCE(sf.leads, 0) AS salesforce_leads,
    COALESCE(sf.opportunities, 0) AS salesforce_opportunities,
    COALESCE(sf.closed_won, 0) AS salesforce_closed_won
FROM 
    dim_date d
    CROSS JOIN dim_campaign c
    LEFT JOIN fact_redtrack rt ON d.date_id = rt.date_id AND c.campaign_id = rt.campaign_id
    LEFT JOIN fact_matomo m ON d.date_id = m.date_id AND c.campaign_id = m.campaign_id
    LEFT JOIN fact_google_ads ga ON d.date_id = ga.date_id AND c.campaign_id = ga.campaign_id
    LEFT JOIN fact_bing_ads ba ON d.date_id = ba.date_id AND c.campaign_id = ba.campaign_id
    LEFT JOIN fact_salesforce sf ON d.date_id = sf.date_id AND c.campaign_id = sf.campaign_id;

-- Create indexes for performance
CREATE INDEX idx_redtrack_date_campaign ON fact_redtrack(date_id, campaign_id);
CREATE INDEX idx_matomo_date_campaign ON fact_matomo(date_id, campaign_id);
CREATE INDEX idx_google_ads_date_campaign ON fact_google_ads(date_id, campaign_id);
CREATE INDEX idx_bing_ads_date_campaign ON fact_bing_ads(date_id, campaign_id);
CREATE INDEX idx_salesforce_date_campaign ON fact_salesforce(date_id, campaign_id);
CREATE INDEX idx_fact_leads_date_campaign ON fact_leads(date_id, campaign_id);
CREATE INDEX idx_fact_sales_date_campaign ON fact_sales(date_id, campaign_id);

-- Create date population function
CREATE OR REPLACE FUNCTION populate_date_dimension(start_date DATE, end_date DATE)
RETURNS VOID AS $$
DECLARE
    loop_date DATE := start_date;
BEGIN
    WHILE loop_date <= end_date LOOP
        INSERT INTO dim_date (
            full_date,
            day_of_week,
            day_name,
            month,
            month_name,
            quarter,
            year,
            is_weekend
        )
        VALUES (
            loop_date,
            EXTRACT(DOW FROM loop_date),
            TO_CHAR(loop_date, 'Day'),
            EXTRACT(MONTH FROM loop_date),
            TO_CHAR(loop_date, 'Month'),
            EXTRACT(QUARTER FROM loop_date),
            EXTRACT(YEAR FROM loop_date),
            CASE WHEN EXTRACT(DOW FROM loop_date) IN (0, 6) THEN TRUE ELSE FALSE END
        )
        ON CONFLICT (full_date) DO NOTHING;
        
        loop_date := loop_date + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Example usage:
-- SELECT populate_date_dimension('2023-01-01', '2025-12-31');
