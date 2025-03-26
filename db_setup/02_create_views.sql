-- PART 2: Create views (run this AFTER creating all tables successfully)

-- Create a basic unified view for ad metrics
CREATE OR REPLACE VIEW public.sm_unified_ads_metrics AS
SELECT
    'google' as platform, -- Simplified platform name
    g.network as network,
    g.date,
    g.campaign_id::TEXT as campaign_id, -- Cast to TEXT
    COALESCE(m.pretty_campaign_name, g.campaign_name) as campaign_name,
    g.campaign_name as original_campaign_name,
    g.location_id,
    l.region_code,
    l.location_name,
    l.country,
    COALESCE(m.campaign_category, 'Uncategorized') as campaign_category,
    COALESCE(m.campaign_type, 'Uncategorized') as campaign_type,
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
LEFT JOIN
    public.sm_campaign_name_mapping m
        ON LOWER(m.source_system) = 'google ads' -- Case-insensitive literal
        AND TRIM(m.external_campaign_id)::TEXT = TRIM(g.campaign_id::TEXT) -- Robust comparison

UNION ALL

SELECT
    'bing' as platform, -- Simplified platform name
    b.network as network,
    b.date,
    b.campaign_id::TEXT as campaign_id, -- Cast to TEXT
    COALESCE(m.pretty_campaign_name, b.campaign_name) as campaign_name,
    b.campaign_name as original_campaign_name,
    b.location_id,
    l.region_code,
    l.location_name,
    l.country,
    COALESCE(m.campaign_category, 'Uncategorized') as campaign_category,
    COALESCE(m.campaign_type, 'Uncategorized') as campaign_type,
    b.impressions,
    b.clicks,
    b.cost,
    b.conversions,
    b.conversion_rate,
    b.cost_per_conversion
FROM 
    public.sm_fact_bing_ads b
LEFT JOIN 
    public.sm_dim_location l ON b.location_id = l.location_id
LEFT JOIN
    public.sm_campaign_name_mapping m
        ON LOWER(m.source_system) = 'bing ads' -- Case-insensitive literal
        AND TRIM(m.external_campaign_id)::TEXT = TRIM(b.campaign_id::TEXT) -- Robust comparison

UNION ALL

SELECT
    'redtrack' as platform, -- Already simple
    NULL as network,
    r.date,
    r.campaign_id::TEXT as campaign_id, -- Cast to TEXT
    COALESCE(m.pretty_campaign_name, r.campaign_name) as campaign_name,
    r.campaign_name as original_campaign_name,
    NULL as location_id,
    NULL as region_code,
    NULL as location_name,
    NULL as country,
    COALESCE(m.campaign_category, 'Uncategorized') as campaign_category,
    COALESCE(m.campaign_type, 'Uncategorized') as campaign_type,
    NULL::BIGINT as impressions, -- Redtrack fact table doesn't have these
    r.clicks, -- It has clicks
    NULL::DECIMAL as cost, -- Redtrack fact table doesn't have cost
    r.conversions, -- It has conversions
    NULL::DECIMAL as conversion_rate, -- Redtrack fact table doesn't have these rates
    NULL::DECIMAL as cost_per_conversion -- Redtrack fact table doesn't have these rates
FROM
    public.sm_fact_redtrack r
LEFT JOIN
    public.sm_campaign_name_mapping m
        ON LOWER(m.source_system) = 'redtrack' -- Case-insensitive literal
        AND TRIM(m.external_campaign_id)::TEXT = TRIM(r.campaign_id::TEXT); -- Robust comparison

-- Create a view that combines campaign performance metrics
CREATE OR REPLACE VIEW public.sm_campaign_performance AS
SELECT
    platform,
    COALESCE(network, 'Unknown') as network,
    campaign_id,
    campaign_name,
    original_campaign_name,
    campaign_category,
    campaign_type,
    date,
    SUM(impressions) as impressions,
    SUM(clicks) as clicks,
    SUM(cost) as cost,
    SUM(conversions) as conversions,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(cost) / SUM(clicks) 
        ELSE 0 
    END as cpc,
    CASE 
        WHEN SUM(impressions) > 0 THEN SUM(clicks)::FLOAT / SUM(impressions) 
        ELSE 0 
    END as ctr,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(conversions)::FLOAT / SUM(clicks) 
        ELSE 0 
    END as conversion_rate,
    CASE 
        WHEN SUM(conversions) > 0 THEN SUM(cost) / SUM(conversions) 
        ELSE 0 
    END as cost_per_conversion
FROM 
    public.sm_unified_ads_metrics
GROUP BY
    platform,
    network,
    campaign_id,
    campaign_name,
    original_campaign_name,
    campaign_category,
    campaign_type,
    date;
