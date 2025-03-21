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
        if "://" in debug_url:
            parts = debug_url.split("://")
            if "@" in parts[1]:
                userpass, hostdb = parts[1].split("@", 1)
                if ":" in userpass:
                    user, password = userpass.split(":", 1)
                    debug_url = f"{parts[0]}://{user}:****@{hostdb}"
        
        logger.info(f"Connecting to database: {debug_url}")
        
        # Connect to database
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Create required tables if they don't exist
            create_tables_if_not_exist(conn)
            
            # Add display_order column
            add_display_order_column(conn)
            
            # Add unique constraint (don't remove it) 
            add_unique_constraint(conn)
            
            # Add pretty name columns
            add_pretty_name_columns(conn)
            
            # Add network column to all fact tables
            add_network_column(conn)
            
            # Insert sample data - DISABLED TO AVOID CONFUSION WITH REAL DATA
            # insert_sample_data(conn)
            
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
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

def add_unique_constraint(conn):
    """Add unique constraint on source_system and external_campaign_id if it doesn't exist"""
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
        
        if not constraint_result:
            logger.info("Adding unique constraint on source_system and external_campaign_id")
            conn.execute(text("""
                ALTER TABLE public.sm_campaign_name_mapping
                ADD CONSTRAINT unique_source_system_external_campaign_id UNIQUE (source_system, external_campaign_id)
            """))
            logger.info("Unique constraint added successfully")
        else:
            logger.info("Unique constraint already exists on source_system and external_campaign_id")
    except Exception as e:
        logger.warning(f"Error checking/adding constraints: {str(e)}")
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

def add_network_column(conn):
    """Add network column to all fact tables if it doesn't exist"""
    try:
        # List of tables that should have a network column
        tables_needing_network = [
            'sm_fact_google_ads',
            'sm_fact_bing_ads',
            'sm_fact_redtrack',
            'sm_fact_matomo'
        ]
        
        for table in tables_needing_network:
            # Check if the table exists first
            inspector = inspect(conn)
            if table in inspector.get_table_names():
                # Check if network column exists
                columns = [c['name'] for c in inspector.get_columns(table)]
                if 'network' not in columns:
                    logger.info(f"Adding network column to {table}")
                    conn.execute(text(f"""
                        ALTER TABLE public.{table}
                        ADD COLUMN network VARCHAR(100)
                    """))
                    logger.info(f"network column added to {table}")
                else:
                    logger.info(f"network column already exists in {table}")
    except Exception as e:
        logger.warning(f"Error adding network column: {str(e)}")
        # Continue execution even if this fails

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
                ('Matomo', 'MT001', 'Organic Traffic', 'Organic SEO', 'Organic', 'SEO', NULL)
            """
            conn.execute(text(sample_data_query))
            logger.info("Sample campaign mapping data inserted")
        
        # Define a helper function to check if a column exists in a table
        def column_exists(table, column):
            return column in [c['name'] for c in inspect(conn).get_columns(table)]
        
        # Check each fact table for required columns before inserting data
        fact_tables = ['sm_fact_google_ads', 'sm_fact_bing_ads', 'sm_fact_redtrack', 'sm_fact_matomo']
        for table in fact_tables:
            # Check if the table exists and has data
            count_fact_query = f"SELECT COUNT(*) FROM public.{table}"
            try:
                count_fact_result = conn.execute(text(count_fact_query)).scalar()
                
                # Skip if table already has data
                if count_fact_result > 0:
                    continue
                
                # Check if network column exists in this table
                has_network_column = column_exists(table, 'network')
                
                logger.info(f"Inserting sample data into {table} (network column exists: {has_network_column})")
                
                if table == 'sm_fact_google_ads':
                    # Adjust query based on column existence
                    if has_network_column:
                        query = """
                        INSERT INTO public.sm_fact_google_ads
                            (date, campaign_id, campaign_name, network, impressions, clicks, cost, conversions)
                        VALUES
                            ('2025-03-01', '12345', 'Brand Search Campaign 2025', 'Search', 1000, 150, 250.50, 10),
                            ('2025-03-02', '12345', 'Brand Search Campaign 2025', 'Search', 1200, 180, 300.75, 15)
                        """
                    else:
                        query = """
                        INSERT INTO public.sm_fact_google_ads
                            (date, campaign_id, campaign_name, impressions, clicks, cost, conversions)
                        VALUES
                            ('2025-03-01', '12345', 'Brand Search Campaign 2025', 1000, 150, 250.50, 10),
                            ('2025-03-02', '12345', 'Brand Search Campaign 2025', 1200, 180, 300.75, 15)
                        """
                elif table == 'sm_fact_bing_ads':
                    if has_network_column:
                        query = """
                        INSERT INTO public.sm_fact_bing_ads
                            (date, campaign_id, campaign_name, network, impressions, clicks, cost, conversions)
                        VALUES
                            ('2025-03-01', 'BNG12345', 'Bing Brand Campaign', 'Search', 500, 75, 100.50, 8),
                            ('2025-03-02', 'BNG12345', 'Bing Brand Campaign', 'Search', 600, 90, 120.75, 12)
                        """
                    else:
                        query = """
                        INSERT INTO public.sm_fact_bing_ads
                            (date, campaign_id, campaign_name, impressions, clicks, cost, conversions)
                        VALUES
                            ('2025-03-01', 'BNG12345', 'Bing Brand Campaign', 500, 75, 100.50, 8),
                            ('2025-03-02', 'BNG12345', 'Bing Brand Campaign', 600, 90, 120.75, 12)
                        """
                elif table == 'sm_fact_redtrack':
                    if has_network_column:
                        query = """
                        INSERT INTO public.sm_fact_redtrack
                            (date, campaign_id, campaign_name, network, clicks, conversions, revenue, cost)
                        VALUES
                            ('2025-03-01', 'RT789', 'Facebook Conversion Campaign', 'Facebook', 300, 25, 1250.00, 500.00),
                            ('2025-03-02', 'RT789', 'Facebook Conversion Campaign', 'Facebook', 350, 30, 1500.00, 600.00)
                        """
                    else:
                        query = """
                        INSERT INTO public.sm_fact_redtrack
                            (date, campaign_id, campaign_name, clicks, conversions, revenue, cost)
                        VALUES
                            ('2025-03-01', 'RT789', 'Facebook Conversion Campaign', 300, 25, 1250.00, 500.00),
                            ('2025-03-02', 'RT789', 'Facebook Conversion Campaign', 350, 30, 1500.00, 600.00)
                        """
                elif table == 'sm_fact_matomo':
                    if has_network_column:
                        query = """
                        INSERT INTO public.sm_fact_matomo
                            (date, campaign_id, campaign_name, network, visits, bounces, conversions, revenue)
                        VALUES
                            ('2025-03-01', 'MT001', 'Organic Traffic', NULL, 2000, 400, 50, 2500.00),
                            ('2025-03-02', 'MT001', 'Organic Traffic', NULL, 2200, 440, 55, 2750.00)
                        """
                    else:
                        query = """
                        INSERT INTO public.sm_fact_matomo
                            (date, campaign_id, campaign_name, visits, bounces, conversions, revenue)
                        VALUES
                            ('2025-03-01', 'MT001', 'Organic Traffic', 2000, 400, 50, 2500.00),
                            ('2025-03-02', 'MT001', 'Organic Traffic', 2200, 440, 55, 2750.00)
                        """
                
                conn.execute(text(query))
                logger.info(f"Sample data inserted into {table}")
            except Exception as e:
                logger.warning(f"Error with {table}: {str(e)}")
                # Continue with next table if this one fails
    except Exception as e:
        logger.warning(f"Error inserting sample data: {str(e)}")
        # Continue execution even if this fails

if __name__ == "__main__":
    init_database()
