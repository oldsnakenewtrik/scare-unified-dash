-- PART 1: Create all table structures first
-- No sample data, no views, just the basic structure

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

-- Campaign dimension table
CREATE TABLE public.sm_dim_campaign (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    external_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50),
    account_name VARCHAR(100),
    network VARCHAR(50),
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
    network VARCHAR(50),
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
    network VARCHAR(50),
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

-- Campaign name mapping table
CREATE TABLE public.sm_campaign_name_mapping (
    id SERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL,
    external_campaign_id VARCHAR(50) NOT NULL,
    original_campaign_name VARCHAR(255) NOT NULL,
    pretty_campaign_name VARCHAR(255) NOT NULL,
    campaign_category VARCHAR(100),
    campaign_type VARCHAR(100),
    network VARCHAR(50),
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id)  -- Only enforce uniqueness on the primary key
);

-- Create indexes for better performance on mapping lookups
CREATE INDEX idx_campaign_mapping_source ON public.sm_campaign_name_mapping(source_system);
CREATE INDEX idx_campaign_mapping_external_id ON public.sm_campaign_name_mapping(external_campaign_id);
CREATE INDEX idx_campaign_mapping_source_id ON public.sm_campaign_name_mapping(source_system, external_campaign_id);

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

CREATE INDEX idx_sm_campaign_name_mapping_source ON public.sm_campaign_name_mapping(source_system, external_campaign_id);
