-- migrations/006_add_pretty_network_source.sql
-- Add pretty_network and pretty_source columns to campaign mapping table
ALTER TABLE public.sm_campaign_name_mapping
ADD COLUMN pretty_network VARCHAR(50),
ADD COLUMN pretty_source VARCHAR(50);

-- Optional: Update existing rows if needed (e.g., default to existing values)
-- UPDATE public.sm_campaign_name_mapping
-- SET pretty_network = network, pretty_source = source_system
-- WHERE pretty_network IS NULL OR pretty_source IS NULL;