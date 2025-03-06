-- Just create a single test table
CREATE TABLE public.sm_test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert a test record
INSERT INTO public.sm_test_table (name) VALUES ('Test Record');

-- Verify the record was inserted
SELECT * FROM public.sm_test_table;
