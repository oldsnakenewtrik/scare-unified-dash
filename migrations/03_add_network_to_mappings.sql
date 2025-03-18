-- Migration script to add network information to existing campaign mappings
-- Run this after updating the schema with the network field

-- First, ensure the network column exists (will throw an error if running twice)
DO $$
BEGIN
    BEGIN
        ALTER TABLE public.sm_campaign_name_mapping ADD COLUMN network VARCHAR(50);
    EXCEPTION
        WHEN duplicate_column THEN
            RAISE NOTICE 'network column already exists';
    END;
END $$;

-- Update existing Google Ads mappings with network information from the original data
UPDATE public.sm_campaign_name_mapping m
SET network = g.network
FROM (
    SELECT DISTINCT campaign_id::VARCHAR as external_campaign_id, network
    FROM public.sm_fact_google_ads
) g
WHERE m.source_system = 'Google Ads' 
  AND m.external_campaign_id = g.external_campaign_id
  AND m.network IS NULL;

-- Update existing Bing Ads mappings with network information from the original data
UPDATE public.sm_campaign_name_mapping m
SET network = b.network
FROM (
    SELECT DISTINCT campaign_id::VARCHAR as external_campaign_id, network
    FROM public.sm_fact_bing_ads
) b
WHERE m.source_system = 'Bing Ads' 
  AND m.external_campaign_id = b.external_campaign_id
  AND m.network IS NULL;

-- Note: We are NOT setting default network values for RedTrack or Matomo
-- These will remain NULL until explicitly mapped by the user

-- Verify results
SELECT source_system, COUNT(*) as total_mappings, 
       COUNT(network) as mappings_with_network,
       (COUNT(*) - COUNT(network)) as mappings_missing_network
FROM public.sm_campaign_name_mapping
GROUP BY source_system;
