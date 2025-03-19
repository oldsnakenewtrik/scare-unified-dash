"""
Database migration script to be run on application startup.
This ensures the database schema is up to date before accepting requests.
"""
import logging
import sys
from sqlalchemy import create_engine, text, inspect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_migrations")

def run_migrations(engine):
    """Run all necessary database migrations"""
    try:
        with engine.connect() as conn:
            # Check and add display_order column to campaign mapping table
            add_display_order_column(conn)
            
            # Check and remove unique constraint on source_system and external_campaign_id
            remove_unique_constraint(conn)
            
            conn.commit()
            logger.info("All migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

def add_display_order_column(conn):
    """Add display_order column to sm_campaign_name_mapping if it doesn't exist"""
    inspector = inspect(conn.engine)
    columns = [col['name'] for col in inspector.get_columns('sm_campaign_name_mapping', schema='public')]
    
    if 'display_order' not in columns:
        logger.info("Adding display_order column to sm_campaign_name_mapping")
        conn.execute(text("""
            ALTER TABLE public.sm_campaign_name_mapping 
            ADD COLUMN display_order INT DEFAULT 0
        """))
        logger.info("display_order column added successfully")
    else:
        logger.info("display_order column already exists")

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
        pass

if __name__ == "__main__":
    # Parse args for database connection if run directly
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Run migrations
    run_migrations(engine)
