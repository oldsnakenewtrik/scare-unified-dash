"""
Railway Database Connection Validator

This script validates the database connection in Railway environments and provides
detailed diagnostics for troubleshooting connection issues.
"""
import os
import sys
import time
import logging
import argparse
import traceback
from urllib.parse import urlparse

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("railway_db_validator")

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

def check_environment():
    """Check environment variables related to database connection"""
    logger.info("Checking environment variables...")
    
    env_vars = {
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "PGHOST": os.environ.get("PGHOST"),
        "PGUSER": os.environ.get("PGUSER"),
        "PGDATABASE": os.environ.get("PGDATABASE"),
        "PGPORT": os.environ.get("PGPORT"),
        "RAILWAY_PUBLIC_DOMAIN": os.environ.get("RAILWAY_PUBLIC_DOMAIN"),
        "RAILWAY_ENVIRONMENT": os.environ.get("RAILWAY_ENVIRONMENT")
    }
    
    # Log environment variables (masking sensitive data)
    for var, value in env_vars.items():
        if var == "DATABASE_URL":
            logger.info(f"{var}: {'[SET]' if value else '[NOT SET]'}")
        else:
            logger.info(f"{var}: {value if value else '[NOT SET]'}")
    
    return env_vars

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
    masked_url = mask_password(database_url)
    logger.info(f"Using database URL: {masked_url}")
    
    return database_url

def validate_database_url(url):
    """Validate the database URL format"""
    if not url:
        logger.error("Database URL is empty")
        return False
    
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme != "postgresql":
            logger.error(f"Invalid scheme: {parsed.scheme}, expected 'postgresql'")
            return False
        
        # Check username and password
        if not parsed.username:
            logger.error("Missing username in database URL")
            return False
        
        if not parsed.password:
            logger.warning("Missing password in database URL")
        
        # Check hostname
        if not parsed.hostname:
            logger.error("Missing hostname in database URL")
            return False
        
        # Check database name
        if not parsed.path or parsed.path == "/":
            logger.error("Missing database name in database URL")
            return False
        
        logger.info("Database URL format is valid")
        return True
    except Exception as e:
        logger.error(f"Error validating database URL: {str(e)}")
        return False

def test_connection(url, max_retries=5, retry_delay=5):
    """Test database connection with retry logic"""
    logger.info(f"Testing database connection (max retries: {max_retries})...")
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"Connection attempt {attempt}/{max_retries}")
        
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
                "connect_timeout": 10,
                "application_name": "SCARE Unified Dashboard - Validator"
            }
            
            # Add SSL parameters for Railway
            railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
            if railway_domain and (
                host.endswith("railway.app") or 
                host.endswith("railway.internal") or
                "railway" in host
            ):
                logger.info("Adding SSL parameters for Railway connection")
                conn_params["sslmode"] = "require"
            
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
            
            # Check for required tables
            required_tables = [
                "sm_fact_google_ads", 
                "sm_fact_bing_ads", 
                "sm_fact_facebook_ads", 
                "sm_fact_linkedin_ads",
                "sm_dim_campaign_mapping"
            ]
            missing_tables = [table for table in required_tables if table not in tables]
            
            # Close connection
            cursor.close()
            conn.close()
            
            if result and result[0] == 1:
                logger.info(f"Connection successful (took {elapsed_time:.2f} seconds)")
                logger.info(f"Database version: {version}")
                logger.info(f"Tables in database: {len(tables)}")
                
                if missing_tables:
                    logger.warning(f"Missing required tables: {missing_tables}")
                
                return True, {
                    "success": True,
                    "elapsed_time": elapsed_time,
                    "version": version,
                    "tables": tables,
                    "missing_tables": missing_tables
                }
            else:
                logger.error("Connection test query failed")
                continue
        except psycopg2.OperationalError as e:
            logger.error(f"Connection failed: {str(e)}")
            
            if attempt < max_retries:
                delay = retry_delay * attempt
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                return False, {
                    "success": False,
                    "error": str(e),
                    "error_type": "OperationalError"
                }
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if attempt < max_retries:
                delay = retry_delay * attempt
                logger.info(f"Retrying in {delay} seconds...")
                time.time(delay)
            else:
                return False, {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
    
    return False, {
        "success": False,
        "error": "Max retries exceeded",
        "error_type": "MaxRetriesExceeded"
    }

def check_network_connectivity(host, port):
    """Test basic network connectivity to the database host"""
    logger.info(f"Testing network connectivity to {host}:{port}...")
    
    try:
        import socket
        
        # Create a socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        # Try to connect
        start_time = time.time()
        result = sock.connect_ex((host, port))
        elapsed_time = time.time() - start_time
        
        # Close the socket
        sock.close()
        
        if result == 0:
            logger.info(f"Network connection successful (took {elapsed_time:.2f} seconds)")
            return True
        else:
            logger.error(f"Network connection failed with error code {result}")
            return False
    except Exception as e:
        logger.error(f"Network connection error: {str(e)}")
        return False

def check_column_exists(conn, table, column):
    """Check if a column exists in a table"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = '{table}' AND column_name = '{column}'
            )
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    except Exception as e:
        logger.error(f"Error checking if column {column} exists in table {table}: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Railway Database Connection Validator")
    parser.add_argument("--retry", type=int, default=5, help="Number of connection retry attempts")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common issues")
    args = parser.parse_args()
    
    logger.info("Starting Railway database connection validation...")
    
    # Check environment variables
    env_vars = check_environment()
    
    # Get database URL
    database_url = get_database_url()
    if not database_url:
        logger.error("No database URL available. Cannot proceed with validation.")
        return 1
    
    # Validate database URL
    if not validate_database_url(database_url):
        logger.error("Invalid database URL. Cannot proceed with validation.")
        return 1
    
    # Parse the URL for network connectivity test
    parsed = urlparse(database_url)
    host = parsed.hostname
    port = parsed.port or 5432
    
    # Check network connectivity
    if not check_network_connectivity(host, port):
        logger.warning("Network connectivity test failed. Connection may still work with proper credentials.")
    
    # Test database connection
    success, results = test_connection(database_url, max_retries=args.retry)
    
    if success:
        logger.info("Database connection validation passed!")
        
        # Check for missing columns if fix flag is set
        if args.fix and "missing_tables" not in results:
            try:
                # Connect to the database
                parsed = urlparse(database_url)
                dbname = parsed.path[1:]
                user = parsed.username
                password = parsed.password
                host = parsed.hostname
                port = parsed.port or 5432
                
                conn_params = {
                    "dbname": dbname,
                    "user": user,
                    "password": password,
                    "host": host,
                    "port": port,
                    "connect_timeout": 10
                }
                
                # Add SSL for Railway
                if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
                    conn_params["sslmode"] = "require"
                
                conn = psycopg2.connect(**conn_params)
                conn.autocommit = True
                
                # Check for network column in bing_ads table
                if not check_column_exists(conn, "sm_fact_bing_ads", "network"):
                    logger.warning("Column 'network' missing from sm_fact_bing_ads table")
                    
                    # Add the column
                    cursor = conn.cursor()
                    cursor.execute("""
                        ALTER TABLE sm_fact_bing_ads
                        ADD COLUMN IF NOT EXISTS network VARCHAR(255) DEFAULT 'Search'
                    """)
                    cursor.close()
                    logger.info("Added 'network' column to sm_fact_bing_ads table")
                
                # Check for network column in other tables
                for table in ["sm_fact_google_ads", "sm_fact_facebook_ads", "sm_fact_linkedin_ads"]:
                    if not check_column_exists(conn, table, "network"):
                        logger.warning(f"Column 'network' missing from {table} table")
                        
                        # Add the column
                        cursor = conn.cursor()
                        cursor.execute(f"""
                            ALTER TABLE {table}
                            ADD COLUMN IF NOT EXISTS network VARCHAR(255) DEFAULT 'Search'
                        """)
                        cursor.close()
                        logger.info(f"Added 'network' column to {table} table")
                
                # Check for network columns in campaign mapping table
                for column in ["network", "pretty_network"]:
                    if not check_column_exists(conn, "sm_dim_campaign_mapping", column):
                        logger.warning(f"Column '{column}' missing from sm_dim_campaign_mapping table")
                        
                        # Add the column
                        cursor = conn.cursor()
                        cursor.execute(f"""
                            ALTER TABLE sm_dim_campaign_mapping
                            ADD COLUMN IF NOT EXISTS {column} VARCHAR(255) DEFAULT 'Search'
                        """)
                        cursor.close()
                        logger.info(f"Added '{column}' column to sm_dim_campaign_mapping table")
                
                conn.close()
            except Exception as e:
                logger.error(f"Error fixing missing columns: {str(e)}")
        
        return 0
    else:
        logger.error(f"Database connection validation failed: {results.get('error', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
