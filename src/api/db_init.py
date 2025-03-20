"""
Database initialization script for SCARE Unified Dashboard.
Creates all required tables if they don't exist and runs necessary migrations.
"""
import logging
import sys
import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_init")

# Load environment variables
load_dotenv()

# Get database URL from environment - add more fallbacks
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL") or "postgresql://scare_user:scare_password@postgres:5432/scare_metrics"

def init_database():
    """Initialize the database with required tables and run migrations"""
    try:
        # Print database URL for debugging (masking password)
        debug_url = DATABASE_URL
        if "://" in debug_url and "@" in debug_url:
            prefix, suffix = debug_url.split("://", 1)
            auth, remainder = suffix.split("@", 1)
            if ":" in auth:
                user, _ = auth.split(":", 1)
                masked_url = f"{prefix}://{user}:****@{remainder}"
                logger.info(f"Connecting to database: {masked_url}")
        
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Execute everything in a transaction block
            with conn.begin():
                # Create tables if they don't exist
                create_tables_if_not_exist(conn)
                
                # Run additional migrations
                add_display_order_column(conn)
                remove_unique_constraint(conn)
                add_pretty_name_columns(conn)
                
                # Insert sample data if tables are empty
                insert_sample_data(conn)
                
                # No conn.commit() needed with transaction block
                logger.info("Database initialization completed successfully")
                
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

def create_tables_if_not_exist(conn):
    """Create all required tables if they don't exist"""
    inspector = inspect(conn.engine)
    existing_tables = inspector.get_table_names()
    
    # Check for campaign mapping table
    if 'sm_campaign_name_mapping' not in existing_tables:
        logger.info("Creating sm_campaign_name_mapping table")
        conn.execute(text("""
            CREATE TABLE public.sm_campaign_name_mapping (
                id SERIAL PRIMARY KEY,
                source_system VARCHAR(50) NOT NULL,
                external_campaign_id VARCHAR(255) NOT NULL,
                original_campaign_name VARCHAR(255) NOT NULL,
                pretty_campaign_name VARCHAR(255),
                pretty_source VARCHAR(100),
                pretty_network VARCHAR(100),
                campaign_category VARCHAR(100),
                campaign_type VARCHAR(100),
                network VARCHAR(100),
                display_order INT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_mapping_source 
                ON public.sm_campaign_name_mapping (source_system);
                
            CREATE INDEX IF NOT EXISTS idx_mapping_source_id 
                ON public.sm_campaign_name_mapping (source_system, external_campaign_id);
        """))
        logger.info("sm_campaign_name_mapping table created")
    
    # Check for fact tables
    fact_tables = {
        'sm_fact_google_ads': """
            CREATE TABLE public.sm_fact_google_ads (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                campaign_id VARCHAR(255) NOT NULL,
                campaign_name VARCHAR(255) NOT NULL,
                network VARCHAR(100),
                impressions INT DEFAULT 0,
                clicks INT DEFAULT 0,
                cost DECIMAL(12,2) DEFAULT 0,
                conversions INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'sm_fact_bing_ads': """
            CREATE TABLE public.sm_fact_bing_ads (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                campaign_id VARCHAR(255) NOT NULL,
                campaign_name VARCHAR(255) NOT NULL,
                network VARCHAR(100),
                impressions INT DEFAULT 0,
                clicks INT DEFAULT 0,
                cost DECIMAL(12,2) DEFAULT 0,
                conversions INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'sm_fact_matomo': """
            CREATE TABLE public.sm_fact_matomo (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                campaign_id VARCHAR(255) NOT NULL,
                campaign_name VARCHAR(255) NOT NULL,
                network VARCHAR(100),
                visits INT DEFAULT 0,
                bounces INT DEFAULT 0,
                conversions INT DEFAULT 0,
                revenue DECIMAL(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'sm_fact_redtrack': """
            CREATE TABLE public.sm_fact_redtrack (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                campaign_id VARCHAR(255) NOT NULL,
                campaign_name VARCHAR(255) NOT NULL,
                network VARCHAR(100),
                clicks INT DEFAULT 0,
                conversions INT DEFAULT 0,
                revenue DECIMAL(12,2) DEFAULT 0,
                cost DECIMAL(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    }
    
    for table_name, create_sql in fact_tables.items():
        if table_name not in existing_tables:
            logger.info(f"Creating {table_name} table")
            conn.execute(text(create_sql))
            logger.info(f"{table_name} table created")
        else:
            logger.info(f"{table_name} table already exists")

def add_display_order_column(conn):
    """Add display_order column to sm_campaign_name_mapping if it doesn't exist"""
    try:
        inspector = inspect(conn.engine)
        if 'sm_campaign_name_mapping' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('sm_campaign_name_mapping')]
            
            if 'display_order' not in columns:
                logger.info("Adding display_order column to sm_campaign_name_mapping")
                conn.execute(text("""
                    ALTER TABLE public.sm_campaign_name_mapping 
                    ADD COLUMN display_order INT DEFAULT 0
                """))
                logger.info("display_order column added successfully")
            else:
                logger.info("display_order column already exists")
    except Exception as e:
        logger.warning(f"Error checking/adding display_order column: {str(e)}")
        # Continue execution even if this fails

def remove_unique_constraint(conn):
    """Remove unique constraint on source_system and external_campaign_id if it exists"""
    try:
        # Check for constraints on the table
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
        
        constraint_result = conn.execute(text(check_constraint_query)).fetchone()
        
        if constraint_result:
            constraint_name = constraint_result[0]
            logger.info(f"Removing unique constraint: {constraint_name}")
            conn.execute(text(f"""
                ALTER TABLE public.sm_campaign_name_mapping
                DROP CONSTRAINT {constraint_name}
            """))
            logger.info("Unique constraint removed successfully")
        else:
            logger.info("No unique constraint found on source_system and external_campaign_id")
    except Exception as e:
        logger.warning(f"Error checking/removing constraints: {str(e)}")
        # Continue execution even if this fails

def add_pretty_name_columns(conn):
    """Add pretty_network and pretty_source columns to sm_campaign_name_mapping if they don't exist"""
    try:
        logger.info("Checking for pretty_network and pretty_source columns")
        
        # Check if the columns already exist
        check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'sm_campaign_name_mapping'
            AND column_name IN ('pretty_network', 'pretty_source')
        """
        existing_columns = [row[0] for row in conn.execute(text(check_column_query)).fetchall()]
        
        # Add pretty_network column if it doesn't exist
        if 'pretty_network' not in existing_columns:
            logger.info("Adding pretty_network column to sm_campaign_name_mapping")
            conn.execute(text("""
                ALTER TABLE public.sm_campaign_name_mapping 
                ADD COLUMN pretty_network VARCHAR(100)
            """))
            logger.info("pretty_network column added")
        else:
            logger.info("pretty_network column already exists")
            
        # Add pretty_source column if it doesn't exist
        if 'pretty_source' not in existing_columns:
            logger.info("Adding pretty_source column to sm_campaign_name_mapping")
            conn.execute(text("""
                ALTER TABLE public.sm_campaign_name_mapping 
                ADD COLUMN pretty_source VARCHAR(100)
            """))
            logger.info("pretty_source column added")
        else:
            logger.info("pretty_source column already exists")
            
    except Exception as e:
        logger.error(f"Error adding pretty name columns: {str(e)}")
        raise

def insert_sample_data(conn):
    """Insert sample data for testing if tables are empty"""
    try:
        # Check if campaign mapping table has data
        count_query = "SELECT COUNT(*) FROM public.sm_campaign_name_mapping"
        count_result = conn.execute(text(count_query)).scalar()
        
        if count_result == 0:
            logger.info("Inserting sample campaign mapping data")
            sample_data_query = """
            INSERT INTO public.sm_campaign_name_mapping 
                (source_system, external_campaign_id, original_campaign_name, pretty_campaign_name, campaign_category, campaign_type, network) 
            VALUES 
                ('Google Ads', '12345', 'Brand Search Campaign 2025', 'Brand Search', 'Search', 'Brand', 'Search'),
                ('Google Ads', '67890', 'Generic Search Campaign 2025', 'Generic Search', 'Search', 'Non-Brand', 'Search'),
                ('Bing Ads', 'BNG12345', 'Bing Brand Campaign', 'Bing Brand', 'Search', 'Brand', 'Search'),
                ('RedTrack', 'RT789', 'Facebook Conversion Campaign', 'FB Conversion', 'Social', 'Conversion', 'Facebook'),
                ('Matomo', 'MT001', 'Organic Traffic', 'Organic', 'Organic', 'SEO', NULL)
            """
            conn.execute(text(sample_data_query))
            logger.info("Sample campaign mapping data inserted")
            
            # Also insert sample fact data
            fact_data_queries = {
                'sm_fact_google_ads': """
                INSERT INTO public.sm_fact_google_ads
                    (date, campaign_id, campaign_name, network, impressions, clicks, cost, conversions)
                VALUES
                    ('2025-03-01', '12345', 'Brand Search Campaign 2025', 'Search', 1000, 150, 250.50, 10),
                    ('2025-03-02', '12345', 'Brand Search Campaign 2025', 'Search', 1200, 180, 300.75, 15),
                    ('2025-03-01', '67890', 'Generic Search Campaign 2025', 'Search', 5000, 250, 750.25, 5)
                """,
                'sm_fact_bing_ads': """
                INSERT INTO public.sm_fact_bing_ads
                    (date, campaign_id, campaign_name, network, impressions, clicks, cost, conversions)
                VALUES
                    ('2025-03-01', 'BNG12345', 'Bing Brand Campaign', 'Search', 500, 75, 100.50, 8),
                    ('2025-03-02', 'BNG12345', 'Bing Brand Campaign', 'Search', 600, 90, 120.75, 12)
                """,
                'sm_fact_redtrack': """
                INSERT INTO public.sm_fact_redtrack
                    (date, campaign_id, campaign_name, network, clicks, conversions, revenue, cost)
                VALUES
                    ('2025-03-01', 'RT789', 'Facebook Conversion Campaign', 'Facebook', 300, 25, 1250.00, 500.00),
                    ('2025-03-02', 'RT789', 'Facebook Conversion Campaign', 'Facebook', 350, 30, 1500.00, 600.00)
                """,
                'sm_fact_matomo': """
                INSERT INTO public.sm_fact_matomo
                    (date, campaign_id, campaign_name, network, visits, bounces, conversions, revenue)
                VALUES
                    ('2025-03-01', 'MT001', 'Organic Traffic', NULL, 2000, 400, 50, 2500.00),
                    ('2025-03-02', 'MT001', 'Organic Traffic', NULL, 2200, 440, 55, 2750.00)
                """
            }
            
            for table_name, query in fact_data_queries.items():
                count_fact_query = f"SELECT COUNT(*) FROM public.{table_name}"
                count_fact_result = conn.execute(text(count_fact_query)).scalar()
                
                if count_fact_result == 0:
                    logger.info(f"Inserting sample data into {table_name}")
                    conn.execute(text(query))
                    logger.info(f"Sample data inserted into {table_name}")
    except Exception as e:
        logger.warning(f"Error inserting sample data: {str(e)}")
        # Continue execution even if this fails

if __name__ == "__main__":
    init_database()
