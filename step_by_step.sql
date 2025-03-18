-- Step 1: Create the dimension tables
CREATE TABLE scare_metrics.dim_location (
    location_id SERIAL PRIMARY KEY,
    region_code VARCHAR(10) NOT NULL,
    location_name VARCHAR(100) NOT NULL,
    geo_target_id BIGINT,
    country VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Insert some location data
INSERT INTO scare_metrics.dim_location 
(region_code, location_name, geo_target_id, country) 
VALUES
('WA', 'Washington', 1014895, 'United States'),
('AZ', 'Arizona', 21136, 'United States'),
('AB', 'Alberta', 1019681, 'Canada');

-- Step 3: Create the campaign dimension table
CREATE TABLE scare_metrics.dim_campaign (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    external_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50),
    account_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 4: Create mapping table
CREATE TABLE scare_metrics.campaign_location (
    id SERIAL PRIMARY KEY,
    campaign_id INT REFERENCES scare_metrics.dim_campaign(campaign_id),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, location_id)
);

-- Step 5: Create Google Ads fact table
CREATE TABLE scare_metrics.fact_google_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(12,2) DEFAULT 0,
    conversions DECIMAL(10,2) DEFAULT 0,
    source VARCHAR(50) DEFAULT 'Google Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 6: Create Bing Ads fact table
CREATE TABLE scare_metrics.fact_bing_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(12,2) DEFAULT 0,
    conversions DECIMAL(10,2) DEFAULT 0,
    source VARCHAR(50) DEFAULT 'Bing Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 7: Create Matomo fact table
CREATE TABLE scare_metrics.fact_matomo (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT,
    campaign_name VARCHAR(255),
    site_id INT NOT NULL,
    site_name VARCHAR(100),
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    visits BIGINT DEFAULT 0,
    unique_visitors BIGINT DEFAULT 0,
    bounce_rate DECIMAL(8,4) DEFAULT 0,
    page_views BIGINT DEFAULT 0,
    source VARCHAR(50) DEFAULT 'Matomo',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 8: Create RedTrack fact table
CREATE TABLE scare_metrics.fact_redtrack (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    tracker_id VARCHAR(50) NOT NULL,
    location_id INT REFERENCES scare_metrics.dim_location(location_id),
    clicks BIGINT DEFAULT 0,
    conversions BIGINT DEFAULT 0,
    revenue DECIMAL(12,2) DEFAULT 0,
    profit DECIMAL(12,2) DEFAULT 0,
    leads BIGINT DEFAULT 0,
    sales BIGINT DEFAULT 0,
    source VARCHAR(50) DEFAULT 'RedTrack',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 9: Create basic indexes
CREATE INDEX idx_google_ads_date ON scare_metrics.fact_google_ads(date);
CREATE INDEX idx_google_ads_campaign ON scare_metrics.fact_google_ads(campaign_id);
CREATE INDEX idx_bing_ads_date ON scare_metrics.fact_bing_ads(date);
CREATE INDEX idx_bing_ads_campaign ON scare_metrics.fact_bing_ads(campaign_id);
CREATE INDEX idx_matomo_date ON scare_metrics.fact_matomo(date);
CREATE INDEX idx_redtrack_date ON scare_metrics.fact_redtrack(date);

-- Step 10: Create a simple unified view
CREATE OR REPLACE VIEW scare_metrics.unified_ads_metrics AS
SELECT 
    'google_ads' as platform,
    g.date,
    g.campaign_id,
    g.campaign_name,
    g.location_id,
    l.region_code,
    l.location_name,
    l.country,
    g.impressions,
    g.clicks,
    g.cost,
    g.conversions
FROM 
    scare_metrics.fact_google_ads g
LEFT JOIN 
    scare_metrics.dim_location l ON g.location_id = l.location_id

UNION ALL

SELECT 
    'bing_ads' as platform,
    b.date,
    b.campaign_id,
    b.campaign_name,
    b.location_id,
    l.region_code,
    l.location_name,
    l.country,
    b.impressions,
    b.clicks,
    b.cost,
    b.conversions
FROM 
    scare_metrics.fact_bing_ads b
LEFT JOIN 
    scare_metrics.dim_location l ON b.location_id = l.location_id;
