-- migrations/007_add_system_status_table.sql

-- Create a table to store system status flags
CREATE TABLE IF NOT EXISTS public.system_status (
    status_key VARCHAR(100) PRIMARY KEY,
    status_value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Add an initial status if needed, otherwise the script will create it
-- INSERT INTO public.system_status (status_key, status_value) 
-- VALUES ('google_ads_auth_status', 'unknown')
-- ON CONFLICT (status_key) DO NOTHING;

-- Add a trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW(); 
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to the system_status table
DO $$
BEGIN
   IF NOT EXISTS (
       SELECT 1 FROM pg_trigger 
       WHERE tgname = 'update_system_status_updated_at' AND tgrelid = 'public.system_status'::regclass
   ) THEN
       CREATE TRIGGER update_system_status_updated_at
       BEFORE UPDATE ON public.system_status
       FOR EACH ROW
       EXECUTE FUNCTION update_updated_at_column();
   END IF;
END $$;

-- Add comment to the table
COMMENT ON TABLE public.system_status IS 'Stores key-value pairs for system status monitoring, e.g., external API connection health.';