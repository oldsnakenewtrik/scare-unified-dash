-- PART 2: Create views (run this AFTER creating all tables successfully)

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
