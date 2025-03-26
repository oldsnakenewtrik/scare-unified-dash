"""
Script to execute the migration SQL file in Railway's PostgreSQL database.
Run with: railway run python execute_migration.py
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("execute_migration")

def mask_password(url):
    """Mask password in database URL for logging"""
    if not url or "://" not in url:
        return url
    
    try:
        parts = url.split("://")
        if "@" in parts[1]:
            userpass, hostdb = parts[1].split("@", 1)
            if ":" in userpass:
                user, password = userpass.split(":", 1)
                return f"{parts[0]}://{user}:****@{hostdb}"
    except Exception:
        pass
    
    return url

def get_database_url():
    """Get database URL from environment variables"""
    # Try to get the database URL from the environment
    database_url = os.environ.get("DATABASE_URL")
    
    # If not found, try to construct it from individual components
    if not database_url:
        logger.warning("DATABASE_URL not found in environment variables")
        
        # Try to get individual components
        host = os.environ.get("PGHOST")
        user = os.environ.get("PGUSER")
        password = os.environ.get("PGPASSWORD")
        database = os.environ.get("PGDATABASE")
        port = os.environ.get("PGPORT", "5432")
        
        # Check if we have all required components
        if host and user and password and database:
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            logger.info("Constructed database URL from individual components")
        else:
            logger.error("Could not construct database URL from environment variables")
            return None
    
    # Log masked URL for debugging
    masked_url = mask_password(database_url)
    logger.info(f"Using database URL: {masked_url}")
    
    return database_url

def execute_migration_sql(sql_file_path):
    """Execute the SQL migration file"""
    logger.info(f"Executing migration SQL file: {sql_file_path}")
    
    # Get database URL
    database_url = get_database_url()
    if not database_url:
        logger.error("No database URL available. Cannot proceed with migration.")
        return False
    
    try:
        # Check if file exists
        if not os.path.exists(sql_file_path):
            logger.error(f"SQL file not found: {sql_file_path}")
            return False
        
        # Read SQL file
        with open(sql_file_path, 'r') as file:
            sql_content = file.read()
        
        logger.info(f"Read {len(sql_content)} bytes from SQL file")
        
        # Create engine with SSL if in Railway
        if "railway" in database_url:
            engine = create_engine(database_url, connect_args={"sslmode": "require"})
        else:
            engine = create_engine(database_url)
        
        logger.info("Connecting to database...")
        
        # Connect to the database and execute SQL
        with engine.connect() as connection:
            # Execute the SQL statements
            logger.info("Executing SQL migration...")
            connection.execute(text(sql_content))
            connection.commit()
            
            # Verify the column was added
            verify_query = """
            SELECT 
                table_name, 
                column_name, 
                data_type 
            FROM 
                information_schema.columns 
            WHERE 
                table_schema = 'public' 
                AND table_name = 'sm_fact_bing_ads' 
                AND column_name = 'network'
            """
            
            result = connection.execute(text(verify_query)).fetchone()
            
            if result:
                logger.info(f"Column verified: {result}")
                return True
            else:
                logger.warning("Column 'network' not found in sm_fact_bing_ads table after migration")
                return False
            
    except Exception as e:
        logger.error(f"Error executing migration SQL: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting migration execution...")
    
    # Path to the migration SQL file
    sql_file_path = "migrations/005_add_network_to_bing_ads.sql"
    
    # Execute the migration
    success = execute_migration_sql(sql_file_path)
    
    if success:
        logger.info("Migration executed successfully!")
        return 0
    else:
        logger.error("Migration execution failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
