-- SCARE Unified Metrics Dashboard - Tables Only
-- Integrates data from Google Ads, Bing Ads, Matomo, and RedTrack with geographic targeting

-- Create the schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS scare_metrics;

-- Set the search path to use our schema
SET search_path TO scare_metrics;

-- Geographic location dimension table
CREATE TABLE IF NOT EXISTS scare_metrics.dim_location (
    location_id SERIAL PRIMARY KEY,
    region_code VARCHAR(10) NOT NULL,
    location_name VARCHAR(100) NOT NULL,
    geo_target_id BIGINT,
    country VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert location data
INSERT INTO scare_metrics.dim_location 
(region_code, location_name, geo_target_id, country) 
VALUES
-- Canadian Provinces
('AB', 'Alberta', 1019681, 'Canada'),
('BC', 'British Columbia', 1015969, 'Canada'),
('MB', 'Manitoba', 1016204, 'Canada'),
('NB', 'New Brunswick', 1022294, 'Canada'),
('NL', 'Newfoundland and Labrador', 1016632, 'Canada'),
('NS', 'Nova Scotia', 1016670, 'Canada'),
('NT', 'Northwest Territories', 1016671, 'Canada'),
('NU', 'Nunavut', 1016206, 'Canada'),
('ON', 'Ontario', 1028132, 'Canada'),
('PE', 'Prince Edward Island', 1016208, 'Canada'),
('QC', 'Quebec', 1016209, 'Canada'),
('SK', 'Saskatchewan', 1016210, 'Canada'),
('YT', 'Yukon', 1025432, 'Canada'),
-- US States
('AL', 'Alabama', 21133, 'United States'),
('AK', 'Alaska', 21132, 'United States'),
('AZ', 'Arizona', 21136, 'United States'),
('AR', 'Arkansas', 21135, 'United States'),
('CA', 'California', 21137, 'United States'),
('CO', 'Colorado', 21138, 'United States'),
('CT', 'Connecticut', 21139, 'United States'),
('DE', 'Delaware', 1023660, 'United States'),
('FL', 'Florida', 21142, 'United States'),
('GA', 'Georgia', 21143, 'United States'),
('HI', 'Hawaii', 21144, 'United States'),
('ID', 'Idaho', 21146, 'United States'),
('IL', 'Illinois', 21147, 'United States'),
('IN', 'Indiana', 1024959, 'United States'),
('IA', 'Iowa', 21145, 'United States'),
('KS', 'Kansas', 1016592, 'United States'),
('KY', 'Kentucky', 21150, 'United States'),
('LA', 'Louisiana', 1020459, 'United States'),
('ME', 'Maine', 1023112, 'United States'),
('MD', 'Maryland', 21153, 'United States'),
('MA', 'Massachusetts', 21152, 'United States'),
('MI', 'Michigan', 21155, 'United States'),
('MN', 'Minnesota', 21156, 'United States'),
('MS', 'Mississippi', 21158, 'United States'),
('MO', 'Missouri', 21157, 'United States'),
('MT', 'Montana', 21159, 'United States'),
('NE', 'Nebraska', 21162, 'United States'),
('NV', 'Nevada', 1015940, 'United States'),
('NH', 'New Hampshire', 21163, 'United States'),
('NJ', 'New Jersey', 21164, 'United States'),
('NM', 'New Mexico', 21165, 'United States'),
('NY', 'New York', 1023191, 'United States'),
('NC', 'North Carolina', 21160, 'United States'),
('ND', 'North Dakota', 21161, 'United States'),
('OH', 'Ohio', 21168, 'United States'),
('OK', 'Oklahoma', 21169, 'United States'),
('OR', 'Oregon', 1020524, 'United States'),
('PA', 'Pennsylvania', 21171, 'United States'),
('RI', 'Rhode Island', 21172, 'United States'),
('SC', 'South Carolina', 21173, 'United States'),
('SD', 'South Dakota', 21174, 'United States'),
('TN', 'Tennessee', 21175, 'United States'),
('TX', 'Texas', 21176, 'United States'),
('UT', 'Utah', 21177, 'United States'),
('VT', 'Vermont', 1016922, 'United States'),
('VA', 'Virginia', 21178, 'United States'),
('WA', 'Washington', 1014895, 'United States'),
('WV', 'West Virginia', 21183, 'United States'),
('WI', 'Wisconsin', 21182, 'United States'),
('WY', 'Wyoming', 1020156, 'United States'),
('DC', 'District of Columbia', 21140, 'United States');

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

-- Campaign-Location mapping (many-to-many relationship)
CREATE TABLE IF NOT EXISTS scare_metrics.campaign_location (
    id SERIAL PRIMARY KEY,
    campaign_id INT REFERENCES scare_metrics.dim_campaign(campaign_id),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, location_id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_campaign_location_campaign ON scare_metrics.campaign_location(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_location_location ON scare_metrics.campaign_location(location_id);

-- Google Ads fact table - based on reporting API structure
CREATE TABLE IF NOT EXISTS scare_metrics.fact_google_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    
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

-- Bing Ads fact table
CREATE TABLE IF NOT EXISTS scare_metrics.fact_bing_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    
    -- Impression metrics
    impressions BIGINT DEFAULT 0,
    impression_reach BIGINT DEFAULT 0,
    
    -- Click metrics
    clicks BIGINT DEFAULT 0,
    click_through_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Cost metrics
    cost DECIMAL(12,2) DEFAULT 0,
    average_cpc DECIMAL(12,2) DEFAULT 0,
    average_cpm DECIMAL(12,2) DEFAULT 0,
    
    -- Conversion metrics
    conversions DECIMAL(10,2) DEFAULT 0,
    conversion_rate DECIMAL(8,4) DEFAULT 0,
    cost_per_conversion DECIMAL(12,2) DEFAULT 0,
    conversion_value DECIMAL(12,2) DEFAULT 0,
    value_per_conversion DECIMAL(12,2) DEFAULT 0,
    
    -- Status fields
    source VARCHAR(50) DEFAULT 'Bing Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Matomo web analytics fact table
CREATE TABLE IF NOT EXISTS scare_metrics.fact_matomo (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT, -- May be NULL if not associated with a campaign
    campaign_name VARCHAR(255),
    site_id INT NOT NULL,
    site_name VARCHAR(100),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    
    -- Visit metrics
    visits BIGINT DEFAULT 0,
    unique_visitors BIGINT DEFAULT 0,
    bounce_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Page metrics
    page_views BIGINT DEFAULT 0,
    pages_per_visit DECIMAL(8,2) DEFAULT 0,
    avg_time_on_site DECIMAL(10,2) DEFAULT 0, -- in seconds
    
    -- Conversion metrics
    goal_conversions BIGINT DEFAULT 0,
    goal_conversion_rate DECIMAL(8,4) DEFAULT 0,
    goal_revenue DECIMAL(12,2) DEFAULT 0,
    
    -- Entry/Exit metrics
    entry_pages BIGINT DEFAULT 0,
    exit_pages BIGINT DEFAULT 0,
    exit_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Status fields
    source VARCHAR(50) DEFAULT 'Matomo',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RedTrack conversion tracking fact table
CREATE TABLE IF NOT EXISTS scare_metrics.fact_redtrack (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    tracker_id VARCHAR(50) NOT NULL,
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    
    -- Impression and click metrics (if available)
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    ctr DECIMAL(8,4) DEFAULT 0,
    
    -- Cost metrics
    cost DECIMAL(12,2) DEFAULT 0,
    cpc DECIMAL(12,2) DEFAULT 0,
    
    -- Conversion metrics
    conversions BIGINT DEFAULT 0,
    conversion_rate DECIMAL(8,4) DEFAULT 0,
    revenue DECIMAL(12,2) DEFAULT 0,
    profit DECIMAL(12,2) DEFAULT 0,
    roi DECIMAL(8,2) DEFAULT 0, -- Return on investment (percentage)
    
    -- Leads/Sales funnel
    leads BIGINT DEFAULT 0,
    sales BIGINT DEFAULT 0,
    lead_to_sale_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Status fields
    source VARCHAR(50) DEFAULT 'RedTrack',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_google_ads_date ON scare_metrics.fact_google_ads(date);
CREATE INDEX IF NOT EXISTS idx_google_ads_campaign ON scare_metrics.fact_google_ads(campaign_id);
CREATE INDEX IF NOT EXISTS idx_google_ads_location ON scare_metrics.fact_google_ads(location_id);

CREATE INDEX IF NOT EXISTS idx_bing_ads_date ON scare_metrics.fact_bing_ads(date);
CREATE INDEX IF NOT EXISTS idx_bing_ads_campaign ON scare_metrics.fact_bing_ads(campaign_id);
CREATE INDEX IF NOT EXISTS idx_bing_ads_location ON scare_metrics.fact_bing_ads(location_id);

CREATE INDEX IF NOT EXISTS idx_matomo_date ON scare_metrics.fact_matomo(date);
CREATE INDEX IF NOT EXISTS idx_matomo_campaign ON scare_metrics.fact_matomo(campaign_id);
CREATE INDEX IF NOT EXISTS idx_matomo_location ON scare_metrics.fact_matomo(location_id);

CREATE INDEX IF NOT EXISTS idx_redtrack_date ON scare_metrics.fact_redtrack(date);
CREATE INDEX IF NOT EXISTS idx_redtrack_campaign ON scare_metrics.fact_redtrack(campaign_id);
CREATE INDEX IF NOT EXISTS idx_redtrack_location ON scare_metrics.fact_redtrack(location_id);
