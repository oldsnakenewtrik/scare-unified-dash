"""
Database initialization script for SCARE Unified Dashboard.
Creates all required tables if they don't exist and runs necessary migrations.
"""
import logging
import sys
import os
import time
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from dotenv import load_dotenv
import traceback

# Import the database configuration module
from .db_config import get_database_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_init")

# Get database URL from the configuration module
DATABASE_URL = get_database_url()

def connect_with_retry(max_retries=5, delay=5):
    """Attempt to connect to the database with retries"""
    for attempt in range(max_retries):
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
            
            logger.info(f"Connecting to database (attempt {attempt+1}/{max_retries}): {debug_url}")
            
            # Connect to database with a timeout
            engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 10})
            conn = engine.connect()
            logger.info(f"Database connection established successfully after {attempt+1} attempt(s)")
            return engine, conn
        except OperationalError as e:
            logger.error(f"Database connection failed (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("Maximum retry attempts reached. Could not connect to database.")
                # Return None values instead of raising an exception
                return None, None
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("Maximum retry attempts reached. Could not connect to database.")
                # Return None values instead of raising an exception
                return None, None

def init_database():
    """Initialize database by creating required tables if they don't exist"""
    try:
        logger.info("Initializing database...")
        
        # Connect to database with retry
        engine, conn = connect_with_retry()
        
        if engine is None or conn is None:
            logger.error("Failed to connect to database after retries. Skipping database initialization.")
            return False
        
        # Create inspector
        inspector = inspect(engine)
        
        # Get list of existing tables
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create tables if they don't exist
        create_tables_if_not_exist(conn, existing_tables)
        
        # Run migrations
        run_migrations(conn)
        
        # Close connection
        conn.close()
        logger.info("Database initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

def run_migrations(conn):
    """Run database migrations"""
    try:
        logger.info("Running database migrations...")
        
        # Create migrations tracking table if it doesn't exist
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Migrations tracking table created or already exists")
        except Exception as e:
            logger.error(f"Error creating migrations table: {str(e)}")
            return False
        
        # Get list of applied migrations
        try:
            result = conn.execute(text("SELECT name FROM migrations"))
            applied_migrations = [row[0] for row in result]
            logger.info(f"Applied migrations: {applied_migrations}")
        except Exception as e:
            logger.error(f"Error getting applied migrations: {str(e)}")
            applied_migrations = []
        
        # Get list of migration files
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if not os.path.exists(migrations_dir):
            logger.warning(f"Migrations directory not found: {migrations_dir}")
            return True
        
        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
        logger.info(f"Found migration files: {migration_files}")
        
        # Apply migrations that haven't been applied yet
        for migration_file in migration_files:
            if migration_file not in applied_migrations:
                logger.info(f"Applying migration: {migration_file}")
                try:
                    # Read migration file
                    with open(os.path.join(migrations_dir, migration_file), "r") as f:
                        migration_sql = f.read()
                    
                    # Execute migration
                    conn.execute(text(migration_sql))
                    
                    # Record migration as applied
                    conn.execute(
                        text("INSERT INTO migrations (name) VALUES (:name)"),
                        {"name": migration_file}
                    )
                    conn.commit()
                    logger.info(f"Migration applied successfully: {migration_file}")
                except Exception as e:
                    logger.error(f"Error applying migration {migration_file}: {str(e)}")
                    # Continue with other migrations even if one fails
                    continue
        
        logger.info("Database migrations completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        return False

def create_tables_if_not_exist(conn, existing_tables):
    """Create required tables if they don't exist"""
    try:
        logger.info("Creating tables if they don't exist...")
        
        # Create sm_fact_google_ads table if it doesn't exist
        if 'sm_fact_google_ads' not in existing_tables:
            logger.info("Creating sm_fact_google_ads table...")
            try:
                conn.execute(text("""
                    CREATE TABLE sm_fact_google_ads (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        campaign_id VARCHAR(255) NOT NULL,
                        campaign_name VARCHAR(255) NOT NULL,
                        impressions INTEGER NOT NULL,
                        clicks INTEGER NOT NULL,
                        cost NUMERIC(12, 2) NOT NULL,
                        conversions NUMERIC(12, 2) NOT NULL,
                        network VARCHAR(50) DEFAULT 'Search'
                    )
                """))
                conn.commit()
                logger.info("sm_fact_google_ads table created successfully")
            except Exception as e:
                logger.error(f"Error creating sm_fact_google_ads table: {str(e)}")
        
        # Create sm_fact_bing_ads table if it doesn't exist
        if 'sm_fact_bing_ads' not in existing_tables:
            logger.info("Creating sm_fact_bing_ads table...")
            try:
                conn.execute(text("""
                    CREATE TABLE sm_fact_bing_ads (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        campaign_id VARCHAR(255) NOT NULL,
                        campaign_name VARCHAR(255) NOT NULL,
                        impressions INTEGER NOT NULL,
                        clicks INTEGER NOT NULL,
                        cost NUMERIC(12, 2) NOT NULL,
                        conversions NUMERIC(12, 2) NOT NULL,
                        network VARCHAR(50) DEFAULT 'Search'
                    )
                """))
                conn.commit()
                logger.info("sm_fact_bing_ads table created successfully")
            except Exception as e:
                logger.error(f"Error creating sm_fact_bing_ads table: {str(e)}")
        
        # Create sm_fact_facebook_ads table if it doesn't exist
        if 'sm_fact_facebook_ads' not in existing_tables:
            logger.info("Creating sm_fact_facebook_ads table...")
            try:
                conn.execute(text("""
                    CREATE TABLE sm_fact_facebook_ads (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        campaign_id VARCHAR(255) NOT NULL,
                        campaign_name VARCHAR(255) NOT NULL,
                        impressions INTEGER NOT NULL,
                        clicks INTEGER NOT NULL,
                        cost NUMERIC(12, 2) NOT NULL,
                        conversions NUMERIC(12, 2) NOT NULL,
                        network VARCHAR(50) DEFAULT 'Facebook'
                    )
                """))
                conn.commit()
                logger.info("sm_fact_facebook_ads table created successfully")
            except Exception as e:
                logger.error(f"Error creating sm_fact_facebook_ads table: {str(e)}")
        
        # Create campaign_mapping table if it doesn't exist
        if 'campaign_mapping' not in existing_tables:
            logger.info("Creating campaign_mapping table...")
            try:
                conn.execute(text("""
                    CREATE TABLE campaign_mapping (
                        id SERIAL PRIMARY KEY,
                        source_system VARCHAR(50) NOT NULL,
                        external_campaign_id VARCHAR(255) NOT NULL,
                        original_campaign_name VARCHAR(255) NOT NULL,
                        pretty_campaign_name VARCHAR(255) NOT NULL,
                        campaign_category VARCHAR(100),
                        campaign_type VARCHAR(100),
                        network VARCHAR(50),
                        pretty_network VARCHAR(50),
                        pretty_source VARCHAR(50),
                        display_order INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(source_system, external_campaign_id)
                    )
                """))
                conn.commit()
                logger.info("campaign_mapping table created successfully")
            except Exception as e:
                logger.error(f"Error creating campaign_mapping table: {str(e)}")
        
        logger.info("All tables created or already exist")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    init_database()
