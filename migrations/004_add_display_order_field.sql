-- Add display_order field to campaign_name_mapping table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'sm_campaign_name_mapping' 
        AND column_name = 'display_order'
    ) THEN
        ALTER TABLE public.sm_campaign_name_mapping
        ADD COLUMN display_order INT DEFAULT 0;
    END IF;
END $$;

-- Ensure the unique constraint is only on ID
DO $$
BEGIN
    -- Drop the existing constraint if it exists
    IF EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = 'public'
        AND t.relname = 'sm_campaign_name_mapping'
        AND c.conname = 'sm_campaign_name_mapping_source_system_external_campaign_id_key'
    ) THEN
        ALTER TABLE public.sm_campaign_name_mapping
        DROP CONSTRAINT sm_campaign_name_mapping_source_system_external_campaign_id_key;
    END IF;
END $$;
