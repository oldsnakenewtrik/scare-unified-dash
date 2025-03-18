-- SCARE Unified Metrics Dashboard Schema (Public Schema Version)
-- We're using the public schema with prefixed table names since that's working

-- Geographic location dimension table
CREATE TABLE public.sm_dim_location (
    location_id SERIAL PRIMARY KEY,
    region_code VARCHAR(10) NOT NULL,
    location_name VARCHAR(100) NOT NULL,
    geo_target_id BIGINT,
    country VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert just a few sample locations
INSERT INTO public.sm_dim_location 
(region_code, location_name, geo_target_id, country) 
VALUES
('WA', 'Washington', 1014895, 'United States'),
('AZ', 'Arizona', 21136, 'United States'),
('AB', 'Alberta', 1019681, 'Canada');

-- Campaign dimension table
CREATE TABLE public.sm_dim_campaign (
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

-- Campaign-Location mapping
CREATE TABLE public.sm_campaign_location (
    id SERIAL PRIMARY KEY,
    campaign_id INT REFERENCES public.sm_dim_campaign(campaign_id),
    location_id INT REFERENCES public.sm_dim_location(location_id),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, location_id)
);

-- Google Ads fact table
CREATE TABLE public.sm_fact_google_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    location_id INT REFERENCES public.sm_dim_location(location_id),
    
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
    source VARCHAR(50) DEFAULT 'Google Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bing Ads fact table
CREATE TABLE public.sm_fact_bing_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    location_id INT REFERENCES public.sm_dim_location(location_id),
    
    -- Impression metrics
    impressions BIGINT DEFAULT 0,
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
    
    -- Status fields
    source VARCHAR(50) DEFAULT 'Bing Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Matomo web analytics fact table
CREATE TABLE public.sm_fact_matomo (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT,
    campaign_name VARCHAR(255),
    site_id INT NOT NULL,
    site_name VARCHAR(100),
    location_id INT REFERENCES public.sm_dim_location(location_id),
    
    -- Visit metrics
    visits BIGINT DEFAULT 0,
    unique_visitors BIGINT DEFAULT 0,
    bounce_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Page metrics
    page_views BIGINT DEFAULT 0,
    pages_per_visit DECIMAL(8,2) DEFAULT 0,
    avg_time_on_site DECIMAL(10,2) DEFAULT 0,
    
    -- Conversion metrics
    goal_conversions BIGINT DEFAULT 0,
    goal_conversion_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Status fields
    source VARCHAR(50) DEFAULT 'Matomo',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RedTrack conversion tracking fact table
CREATE TABLE public.sm_fact_redtrack (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    tracker_id VARCHAR(50) NOT NULL,
    location_id INT REFERENCES public.sm_dim_location(location_id),
    
    -- Click metrics
    clicks BIGINT DEFAULT 0,
    
    -- Conversion metrics
    conversions BIGINT DEFAULT 0,
    conversion_rate DECIMAL(8,4) DEFAULT 0,
    revenue DECIMAL(12,2) DEFAULT 0,
    profit DECIMAL(12,2) DEFAULT 0,
    roi DECIMAL(8,2) DEFAULT 0,
    
    -- Leads/Sales funnel
    leads BIGINT DEFAULT 0,
    sales BIGINT DEFAULT 0,
    lead_to_sale_rate DECIMAL(8,4) DEFAULT 0,
    
    -- Status fields
    source VARCHAR(50) DEFAULT 'RedTrack',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_sm_google_ads_date ON public.sm_fact_google_ads(date);
CREATE INDEX idx_sm_google_ads_campaign ON public.sm_fact_google_ads(campaign_id);
CREATE INDEX idx_sm_google_ads_location ON public.sm_fact_google_ads(location_id);

CREATE INDEX idx_sm_bing_ads_date ON public.sm_fact_bing_ads(date);
CREATE INDEX idx_sm_bing_ads_campaign ON public.sm_fact_bing_ads(campaign_id);
CREATE INDEX idx_sm_bing_ads_location ON public.sm_fact_bing_ads(location_id);

CREATE INDEX idx_sm_matomo_date ON public.sm_fact_matomo(date);
CREATE INDEX idx_sm_matomo_campaign ON public.sm_fact_matomo(campaign_id);
CREATE INDEX idx_sm_matomo_location ON public.sm_fact_matomo(location_id);

CREATE INDEX idx_sm_redtrack_date ON public.sm_fact_redtrack(date);
CREATE INDEX idx_sm_redtrack_campaign ON public.sm_fact_redtrack(campaign_id);
CREATE INDEX idx_sm_redtrack_location ON public.sm_fact_redtrack(location_id);

-- Create a basic unified view for ad metrics
CREATE OR REPLACE VIEW public.sm_unified_ads_metrics AS
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
    g.conversions,
    g.conversion_rate,
    g.cost_per_conversion
FROM 
    public.sm_fact_google_ads g
LEFT JOIN 
    public.sm_dim_location l ON g.location_id = l.location_id

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
    b.conversions,
    b.conversion_rate,
    b.cost_per_conversion
FROM 
    public.sm_fact_bing_ads b
LEFT JOIN 
    public.sm_dim_location l ON b.location_id = l.location_id;

-- Create a campaign performance view that aggregates metrics by campaign
CREATE OR REPLACE VIEW public.sm_campaign_performance AS
SELECT
    'google_ads' as platform,
    date,
    campaign_id,
    campaign_name,
    SUM(impressions) as impressions,
    SUM(clicks) as clicks,
    SUM(cost) as cost,
    SUM(conversions) as conversions,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(cost) / SUM(clicks)
        ELSE 0 
    END as avg_cpc,
    CASE 
        WHEN SUM(impressions) > 0 THEN SUM(clicks)::FLOAT / SUM(impressions) * 100
        ELSE 0 
    END as ctr,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(conversions)::FLOAT / SUM(clicks) * 100
        ELSE 0 
    END as conversion_rate,
    CASE 
        WHEN SUM(conversions) > 0 THEN SUM(cost) / SUM(conversions)
        ELSE 0 
    END as cost_per_conversion
FROM
    public.sm_fact_google_ads
GROUP BY
    platform, date, campaign_id, campaign_name

UNION ALL

SELECT
    'bing_ads' as platform,
    date,
    campaign_id,
    campaign_name,
    SUM(impressions) as impressions,
    SUM(clicks) as clicks,
    SUM(cost) as cost,
    SUM(conversions) as conversions,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(cost) / SUM(clicks)
        ELSE 0 
    END as avg_cpc,
    CASE 
        WHEN SUM(impressions) > 0 THEN SUM(clicks)::FLOAT / SUM(impressions) * 100
        ELSE 0 
    END as ctr,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(conversions)::FLOAT / SUM(clicks) * 100
        ELSE 0 
    END as conversion_rate,
    CASE 
        WHEN SUM(conversions) > 0 THEN SUM(cost) / SUM(conversions)
        ELSE 0 
    END as cost_per_conversion
FROM
    public.sm_fact_bing_ads
GROUP BY
    platform, date, campaign_id, campaign_name;

-- Insert sample campaign data
INSERT INTO public.sm_dim_campaign
(campaign_name, source_system, external_id, account_id, account_name, is_active)
VALUES
-- Google Ads Campaigns
('SCARE Solar - Search', 'Google Ads', '12345678', '123-456-7890', 'SCARE Google Ads', true),
('SCARE Solar - Display', 'Google Ads', '12345679', '123-456-7890', 'SCARE Google Ads', true),
('SCARE Solar - Video', 'Google Ads', '12345680', '123-456-7890', 'SCARE Google Ads', true),
-- Bing Ads Campaigns
('SCARE Solar - Search', 'Bing Ads', '87654321', '098-765-4321', 'SCARE Bing Ads', true),
('SCARE Solar - Display', 'Bing Ads', '87654322', '098-765-4321', 'SCARE Bing Ads', true),
-- RedTrack Campaigns
('SCARE Solar - Affiliate', 'RedTrack', 'RT123456', 'RT-ACC-1', 'SCARE RedTrack', true);

-- Insert sample campaign-location mappings
-- First, get the campaign and location IDs
WITH campaigns AS (
    SELECT campaign_id, campaign_name, source_system FROM public.sm_dim_campaign
),
locations AS (
    SELECT location_id, region_code FROM public.sm_dim_location
)
-- Then create the mappings
INSERT INTO public.sm_campaign_location
(campaign_id, location_id, is_primary)
SELECT 
    c.campaign_id, 
    l.location_id,
    CASE WHEN c.campaign_name = 'SCARE Solar - Search' AND l.region_code = 'WA' THEN true ELSE false END
FROM 
    campaigns c
CROSS JOIN 
    locations l
WHERE 
    (c.campaign_name = 'SCARE Solar - Search' AND l.region_code IN ('WA', 'AZ')) OR
    (c.campaign_name = 'SCARE Solar - Display' AND l.region_code IN ('WA', 'AB')) OR
    (c.campaign_name = 'SCARE Solar - Video' AND l.region_code IN ('AZ', 'AB')) OR
    (c.campaign_name = 'SCARE Solar - Affiliate' AND l.region_code IN ('WA', 'AZ', 'AB'));

-- Insert sample Google Ads data
INSERT INTO public.sm_fact_google_ads
(date, campaign_id, campaign_name, account_id, account_name, location_id, impressions, clicks, cost, conversions, conversion_rate, cost_per_conversion)
SELECT
    (CURRENT_DATE - (n || ' days')::INTERVAL)::DATE as date,
    c.campaign_id,
    c.campaign_name,
    '123-456-7890' as account_id,
    'SCARE Google Ads' as account_name,
    cl.location_id,
    FLOOR(RANDOM() * 10000) + 1000 as impressions,
    FLOOR(RANDOM() * 500) + 50 as clicks,
    (RANDOM() * 1000 + 100)::DECIMAL(12,2) as cost,
    FLOOR(RANDOM() * 20) + 1 as conversions,
    (RANDOM() * 10)::DECIMAL(8,4) as conversion_rate,
    (RANDOM() * 100 + 20)::DECIMAL(12,2) as cost_per_conversion
FROM
    public.sm_dim_campaign c
JOIN
    public.sm_campaign_location cl ON c.campaign_id = cl.campaign_id
CROSS JOIN
    generate_series(0, 29) AS n
WHERE
    c.source_system = 'Google Ads'
ORDER BY
    date DESC, campaign_id;

-- Insert sample Bing Ads data
INSERT INTO public.sm_fact_bing_ads
(date, campaign_id, campaign_name, account_id, account_name, location_id, impressions, clicks, cost, conversions, conversion_rate, cost_per_conversion)
SELECT
    (CURRENT_DATE - (n || ' days')::INTERVAL)::DATE as date,
    c.campaign_id,
    c.campaign_name,
    '098-765-4321' as account_id,
    'SCARE Bing Ads' as account_name,
    cl.location_id,
    FLOOR(RANDOM() * 5000) + 500 as impressions,
    FLOOR(RANDOM() * 250) + 25 as clicks,
    (RANDOM() * 500 + 50)::DECIMAL(12,2) as cost,
    FLOOR(RANDOM() * 10) + 1 as conversions,
    (RANDOM() * 8)::DECIMAL(8,4) as conversion_rate,
    (RANDOM() * 120 + 30)::DECIMAL(12,2) as cost_per_conversion
FROM
    public.sm_dim_campaign c
JOIN
    public.sm_campaign_location cl ON c.campaign_id = cl.campaign_id
CROSS JOIN
    generate_series(0, 29) AS n
WHERE
    c.source_system = 'Bing Ads'
ORDER BY
    date DESC, campaign_id;

-- Insert sample Matomo data
INSERT INTO public.sm_fact_matomo
(date, campaign_id, campaign_name, site_id, site_name, location_id, visits, unique_visitors, bounce_rate, page_views, pages_per_visit, avg_time_on_site, goal_conversions, goal_conversion_rate)
SELECT
    (CURRENT_DATE - (n || ' days')::INTERVAL)::DATE as date,
    c.campaign_id,
    c.campaign_name,
    1 as site_id,
    'SCARE Solar Website' as site_name,
    cl.location_id,
    FLOOR(RANDOM() * 2000) + 200 as visits,
    FLOOR(RANDOM() * 1500) + 150 as unique_visitors,
    (RANDOM() * 60 + 20)::DECIMAL(8,4) as bounce_rate,
    FLOOR(RANDOM() * 8000) + 800 as page_views,
    (RANDOM() * 5 + 1)::DECIMAL(8,2) as pages_per_visit,
    (RANDOM() * 300 + 60)::DECIMAL(10,2) as avg_time_on_site,
    FLOOR(RANDOM() * 30) + 3 as goal_conversions,
    (RANDOM() * 15)::DECIMAL(8,4) as goal_conversion_rate
FROM
    public.sm_dim_campaign c
JOIN
    public.sm_campaign_location cl ON c.campaign_id = cl.campaign_id
CROSS JOIN
    generate_series(0, 29) AS n
ORDER BY
    date DESC, campaign_id;

-- Insert sample RedTrack data
INSERT INTO public.sm_fact_redtrack
(date, campaign_id, campaign_name, tracker_id, location_id, clicks, conversions, conversion_rate, revenue, profit, roi, leads, sales, lead_to_sale_rate)
SELECT
    (CURRENT_DATE - (n || ' days')::INTERVAL)::DATE as date,
    c.campaign_id,
    c.campaign_name,
    'RT-' || c.campaign_id as tracker_id,
    cl.location_id,
    FLOOR(RANDOM() * 300) + 30 as clicks,
    FLOOR(RANDOM() * 15) + 1 as conversions,
    (RANDOM() * 12)::DECIMAL(8,4) as conversion_rate,
    (RANDOM() * 3000 + 300)::DECIMAL(12,2) as revenue,
    (RANDOM() * 1500 + 150)::DECIMAL(12,2) as profit,
    (RANDOM() * 200 + 20)::DECIMAL(8,2) as roi,
    FLOOR(RANDOM() * 25) + 2 as leads,
    FLOOR(RANDOM() * 10) + 1 as sales,
    (RANDOM() * 50)::DECIMAL(8,4) as lead_to_sale_rate
FROM
    public.sm_dim_campaign c
JOIN
    public.sm_campaign_location cl ON c.campaign_id = cl.campaign_id
CROSS JOIN
    generate_series(0, 29) AS n
WHERE
    c.source_system = 'RedTrack'
ORDER BY
    date DESC, campaign_id;
