"""
Railway database connection test script.
This script is designed to run in the Railway environment to test database connectivity.
"""
import os
import sys
import time
import logging
import psycopg2
import traceback
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("railway_db_test")

def mask_sensitive_data(data):
    """Mask sensitive data like passwords for logging"""
    if not data:
        return data
    
    if isinstance(data, str) and "://" in data:
        # Mask password in URL
        try:
            parts = data.split("://")
            if "@" in parts[1]:
                userpass, hostdb = parts[1].split("@", 1)
                if ":" in userpass:
                    user, password = userpass.split(":", 1)
                    return f"{parts[0]}://{user}:****@{hostdb}"
        except Exception:
            pass
    
    return data

def log_environment_variables():
    """Log relevant environment variables for debugging"""
    logger.info("Checking environment variables...")
    
    # List of environment variables to check
    db_env_vars = [
        "DATABASE_URL",
        "PGHOST",
        "PGUSER",
        "PGDATABASE",
        "PGPORT",
        "RAILWAY_PUBLIC_DOMAIN",
        "RAILWAY_ENVIRONMENT",
        "Value"  # Sometimes Railway uses this for DATABASE_URL
    ]
    
    # Log environment variables (masking sensitive data)
    for var in db_env_vars:
        value = os.environ.get(var)
        if var in ["DATABASE_URL", "PGPASSWORD", "Value"]:
            logger.info(f"{var}: {'[SET]' if value else '[NOT SET]'}")
        else:
            logger.info(f"{var}: {value if value else '[NOT SET]'}")

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
            # Check if we have a Value environment variable (sometimes used in Railway)
            value = os.environ.get("Value")
            if value and value.startswith("postgresql://"):
                database_url = value
                logger.info("Using database URL from 'Value' environment variable")
            else:
                logger.error("Could not construct database URL from environment variables")
                return None
    
    # Log masked URL for debugging
    masked_url = mask_sensitive_data(database_url)
    logger.info(f"Using database URL: {masked_url}")
    
    return database_url

def test_psycopg2_connection(url, timeout=10):
    """Test PostgreSQL connection using psycopg2"""
    logger.info("Testing PostgreSQL connection using psycopg2...")
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        dbname = parsed.path[1:]  # Remove leading slash
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        
        # Build connection parameters
        conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "connect_timeout": timeout,
            "application_name": "SCARE Unified Dashboard - Railway Test"
        }
        
        # Try to connect
        start_time = time.time()
        conn = psycopg2.connect(**conn_params)
        elapsed_time = time.time() - start_time
        
        # Test the connection
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Get database information
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        
        # List tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Close connection
        cursor.close()
        conn.close()
        
        if result and result[0] == 1:
            logger.info(f"psycopg2 connection successful (took {elapsed_time:.2f} seconds)")
            logger.info(f"Database version: {version}")
            logger.info(f"Tables in database: {tables}")
            return True, None
        else:
            logger.error("psycopg2 connection test query failed")
            return False, "Connection test query failed"
    except psycopg2.OperationalError as e:
        logger.error(f"psycopg2 connection failed: {str(e)}")
        return False, str(e)
    except Exception as e:
        logger.error(f"psycopg2 connection error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False, str(e)

def run_test():
    """Run the database connection test"""
    logger.info("Starting Railway database connection test...")
    
    # Log environment variables
    log_environment_variables()
    
    # Get database URL
    database_url = get_database_url()
    if not database_url:
        logger.error("No database URL available. Cannot proceed with test.")
        return False
    
    # Test connection
    success, error = test_psycopg2_connection(database_url)
    
    if success:
        logger.info("Database connection test passed!")
        return True
    else:
        logger.error(f"Database connection test failed: {error}")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
