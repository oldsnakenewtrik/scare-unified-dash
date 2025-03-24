"""
Database initialization module for the SCARE Unified Dashboard API.
This module handles database connection, table creation, and migrations.
"""

import os
import sys
import time
import logging
import traceback
from sqlalchemy import create_engine, text, MetaData, Table, Column, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_init")

# Try different import approaches for db_config
try:
    # First try relative import
    from .db_config import get_database_url, get_engine_args, mask_password, create_engine_with_retry
    logger.info("Imported db_config using relative import")
except (ImportError, NameError):
    try:
        # Then try absolute import
        from src.api.db_config import get_database_url, get_engine_args, mask_password, create_engine_with_retry
        logger.info("Imported db_config using absolute import")
    except ImportError:
        # Finally try direct import
        from db_config import get_database_url, get_engine_args, mask_password, create_engine_with_retry
        logger.info("Imported db_config using direct import")

def connect_with_retry(max_retries=5, delay=5):
    """
    Connect to the database with retry logic
    
    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
        
    Returns:
        SQLAlchemy engine or None if connection failed
    """
    try:
        from .db_config import get_database_url, create_engine_with_retry
    except ImportError:
        from src.api.db_config import get_database_url, create_engine_with_retry
    
    # Get the database URL
    database_url = get_database_url()
    if not database_url:
        logger.error("No database URL available")
        return None
    
    # Simple version that doesn't swap URLs mid-connection
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Database connection attempt {attempt}/{max_retries}")
            
            # Log host information for debugging
            if "@" in database_url:
                host_part = database_url.split("@")[1].split("/")[0]
                logger.info(f"Attempting to connect to: {host_part}")
                
            # Create engine with retry logic
            engine = create_engine_with_retry(database_url, 
                connect_args={
                    "connect_timeout": 60,
                    "application_name": "SCARE Unified Dashboard",
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5,
                    "options": "-c statement_timeout=60000",
                    "sslmode": "prefer"
                })
            
            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database connection successful")
                return engine
                
        except Exception as e:
            logger.error(f"Error connecting to database (attempt {attempt}): {e}")
            
            if attempt < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    logger.error(f"Failed to connect to database after {max_retries} attempts")
    return None

def ensure_network_column_exists():
    """
    Ensure that the network column exists in the sm_fact_bing_ads table
    
    This function checks if the network column exists in the sm_fact_bing_ads table
    and adds it if it doesn't exist
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Checking if network column exists in sm_fact_bing_ads table")
    
    # Connect to the database
    engine = connect_with_retry()
    if not engine:
        logger.error("Failed to connect to database, cannot check or add network column")
        return False
    
    try:
        with engine.connect() as conn:
            # Create migrations table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            
            # Check if migration has already been applied
            migration_result = conn.execute(text("""
                SELECT COUNT(*) FROM migrations 
                WHERE migration_name = '005_add_network_to_bing_ads'
            """)).fetchone()
            
            if migration_result and migration_result[0] > 0:
                logger.info("Migration 005_add_network_to_bing_ads already applied")
                return True
            
            # Check if the network column exists
            column_exists_result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'sm_fact_bing_ads' 
                AND column_name = 'network'
            """)).fetchone()
            
            column_exists = column_exists_result and column_exists_result[0] > 0
            
            if column_exists:
                logger.info("Network column already exists in sm_fact_bing_ads table")
                
                # Record the migration as applied
                conn.execute(text("""
                    INSERT INTO migrations (migration_name)
                    VALUES ('005_add_network_to_bing_ads')
                    ON CONFLICT (migration_name) DO NOTHING
                """))
                
                return True
            else:
                logger.info("Network column does not exist in sm_fact_bing_ads table, adding it")
                
                # Add the network column
                try:
                    # Start a transaction
                    with conn.begin():
                        # Add the network column
                        conn.execute(text("""
                            ALTER TABLE public.sm_fact_bing_ads
                            ADD COLUMN network VARCHAR(50) DEFAULT 'Search'
                        """))
                        
                        # Update existing records
                        conn.execute(text("""
                            UPDATE public.sm_fact_bing_ads
                            SET network = 'Search'
                            WHERE network IS NULL
                        """))
                        
                        # Record the migration as applied
                        conn.execute(text("""
                            INSERT INTO migrations (migration_name)
                            VALUES ('005_add_network_to_bing_ads')
                            ON CONFLICT (migration_name) DO NOTHING
                        """))
                    
                    logger.info("Successfully added network column to sm_fact_bing_ads table")
                    return True
                except Exception as e:
                    logger.error(f"Error adding network column to sm_fact_bing_ads table: {e}")
                    return False
    except Exception as e:
        logger.error(f"Error checking or adding network column: {e}")
        return False
    finally:
        # Close the engine
        engine.dispose()

def check_table_exists(connection, table_name):
    """
    Check if a table exists in the database
    """
    try:
        inspector = inspect(connection.engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {str(e)}")
        return False

def check_column_exists(connection, table_name, column_name):
    """
    Check if a column exists in a table
    """
    try:
        inspector = inspect(connection.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.error(f"Error checking if column {column_name} exists in table {table_name}: {str(e)}")
        return False

def create_table_if_not_exists(connection, table_name, columns):
    """
    Create a table if it doesn't exist
    """
    try:
        if not check_table_exists(connection, table_name):
            logger.info(f"Creating table {table_name}")
            metadata = MetaData()
            table = Table(table_name, metadata, *columns)
            metadata.create_all(connection.engine)
            logger.info(f"Table {table_name} created successfully")
            return True
        else:
            logger.info(f"Table {table_name} already exists")
            return False
    except Exception as e:
        logger.error(f"Error creating table {table_name}: {str(e)}")
        return False

def add_column_if_not_exists(connection, table_name, column_name, column_type):
    """
    Add a column to a table if it doesn't exist
    """
    try:
        if check_table_exists(connection, table_name):
            if not check_column_exists(connection, table_name, column_name):
                logger.info(f"Adding column {column_name} to table {table_name}")
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                logger.info(f"Column {column_name} added to table {table_name}")
                return True
            else:
                logger.info(f"Column {column_name} already exists in table {table_name}")
                return False
        else:
            logger.error(f"Table {table_name} does not exist")
            return False
    except Exception as e:
        logger.error(f"Error adding column {column_name} to table {table_name}: {str(e)}")
        return False

def create_migrations_table(connection):
    """
    Create the migrations table if it doesn't exist
    """
    try:
        if not check_table_exists(connection, "migrations"):
            logger.info("Creating migrations table")
            connection.execute(text("""
                CREATE TABLE migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("Migrations table created successfully")
            return True
        else:
            logger.info("Migrations table already exists")
            return False
    except Exception as e:
        logger.error(f"Error creating migrations table: {str(e)}")
        return False

def check_migration_applied(connection, migration_name):
    """
    Check if a migration has been applied
    """
    try:
        if check_table_exists(connection, "migrations"):
            result = connection.execute(
                text("SELECT COUNT(*) FROM migrations WHERE name = :name"),
                {"name": migration_name}
            ).fetchone()
            return result[0] > 0
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking if migration {migration_name} has been applied: {str(e)}")
        return False

def record_migration(connection, migration_name):
    """
    Record that a migration has been applied
    """
    try:
        connection.execute(
            text("INSERT INTO migrations (name) VALUES (:name)"),
            {"name": migration_name}
        )
        logger.info(f"Recorded migration {migration_name}")
        return True
    except Exception as e:
        logger.error(f"Error recording migration {migration_name}: {str(e)}")
        return False

def apply_migration(connection, migration_name, sql):
    """
    Apply a migration and record it
    """
    try:
        # Check if migration has already been applied
        if check_migration_applied(connection, migration_name):
            logger.info(f"Migration {migration_name} has already been applied")
            return True
        
        # Apply the migration
        logger.info(f"Applying migration {migration_name}")
        connection.execute(text(sql))
        
        # Record the migration
        record_migration(connection, migration_name)
        
        logger.info(f"Migration {migration_name} applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying migration {migration_name}: {str(e)}")
        return False

def run_migrations(connection):
    """
    Run all migrations
    """
    try:
        # Create migrations table if it doesn't exist
        create_migrations_table(connection)
        
        # Define migrations
        migrations = [
            {
                "name": "001_create_sm_fact_bing_ads",
                "sql": """
                    CREATE TABLE IF NOT EXISTS sm_fact_bing_ads (
                        id SERIAL PRIMARY KEY,
                        campaign_id VARCHAR(255),
                        campaign_name VARCHAR(255),
                        ad_group_id VARCHAR(255),
                        ad_group_name VARCHAR(255),
                        date DATE,
                        impressions INTEGER,
                        clicks INTEGER,
                        spend NUMERIC(10, 2),
                        conversions INTEGER,
                        revenue NUMERIC(10, 2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
            {
                "name": "002_create_sm_fact_google_ads",
                "sql": """
                    CREATE TABLE IF NOT EXISTS sm_fact_google_ads (
                        id SERIAL PRIMARY KEY,
                        campaign_id VARCHAR(255),
                        campaign_name VARCHAR(255),
                        ad_group_id VARCHAR(255),
                        ad_group_name VARCHAR(255),
                        date DATE,
                        impressions INTEGER,
                        clicks INTEGER,
                        spend NUMERIC(10, 2),
                        conversions INTEGER,
                        revenue NUMERIC(10, 2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
            {
                "name": "003_create_campaign_mappings",
                "sql": """
                    CREATE TABLE IF NOT EXISTS campaign_mappings (
                        id SERIAL PRIMARY KEY,
                        source_campaign_id VARCHAR(255),
                        source_campaign_name VARCHAR(255),
                        source_type VARCHAR(50),
                        target_campaign_id VARCHAR(255),
                        target_campaign_name VARCHAR(255),
                        target_type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
            {
                "name": "004_create_campaign_hierarchy",
                "sql": """
                    CREATE TABLE IF NOT EXISTS campaign_hierarchy (
                        id SERIAL PRIMARY KEY,
                        campaign_id VARCHAR(255),
                        campaign_name VARCHAR(255),
                        parent_id VARCHAR(255),
                        level INTEGER,
                        path VARCHAR(1000),
                        source_type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
            {
                "name": "005_add_network_to_bing_ads",
                "sql": """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'sm_fact_bing_ads' AND column_name = 'network'
                    ) THEN
                        ALTER TABLE sm_fact_bing_ads ADD COLUMN network VARCHAR(50) DEFAULT 'Search';
                    END IF;
                END
                $$;
                """
            }
        ]
        
        # Apply migrations
        for migration in migrations:
            apply_migration(connection, migration["name"], migration["sql"])
        
        logger.info("All migrations applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        return False

def initialize_database():
    """
    Initialize the database connection and run migrations
    Returns the engine and connection if successful, or (None, None) if not
    """
    try:
        # Connect to the database
        engine = connect_with_retry()
        if not engine:
            logger.error("Failed to connect to database")
            return None, None
        
        # Run migrations
        if not run_migrations(engine.connect()):
            logger.error("Failed to run migrations")
            return None, None
        
        logger.info("Database initialized successfully")
        return engine, engine.connect()
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None, None

# For direct execution
if __name__ == "__main__":
    engine, connection = initialize_database()
    if engine and connection:
        print("Database initialized successfully")
        connection.close()
    else:
        print("Failed to initialize database")
