import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env file")
    sys.exit(1)

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Connect to the database
    with engine.connect() as connection:
        # Check if the display_order column exists
        check_column_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'sm_campaign_name_mapping' 
        AND column_name = 'display_order'
        """
        
        result = connection.execute(text(check_column_query)).fetchone()
        
        if not result:
            print("Adding display_order column to sm_campaign_name_mapping table...")
            # Add display_order column
            add_column_query = """
            ALTER TABLE public.sm_campaign_name_mapping
            ADD COLUMN display_order INT DEFAULT 0
            """
            connection.execute(text(add_column_query))
            
            print("Column added successfully!")
        else:
            print("display_order column already exists.")
        
        # Check for unique constraint on (source_system, external_campaign_id)
        check_constraint_query = """
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'public'
        AND rel.relname = 'sm_campaign_name_mapping'
        AND con.contype = 'u'
        AND array_to_string(con.conkey, ',') = 
            (SELECT array_to_string(array_agg(a.attnum ORDER BY a.attnum), ',')
             FROM pg_attribute a
             JOIN pg_class t ON a.attrelid = t.oid
             JOIN pg_namespace n ON t.relnamespace = n.oid
             WHERE n.nspname = 'public'
             AND t.relname = 'sm_campaign_name_mapping'
             AND a.attname IN ('source_system', 'external_campaign_id'))
        """
        
        constraint_result = connection.execute(text(check_constraint_query)).fetchone()
        
        if constraint_result:
            print(f"Removing unique constraint: {constraint_result[0]}...")
            # Remove the unique constraint
            drop_constraint_query = f"""
            ALTER TABLE public.sm_campaign_name_mapping
            DROP CONSTRAINT {constraint_result[0]}
            """
            connection.execute(text(drop_constraint_query))
            
            print("Constraint removed successfully!")
        else:
            print("No unique constraint found on (source_system, external_campaign_id).")
        
        connection.commit()
        print("Migration completed successfully!")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
