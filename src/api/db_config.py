"""
Database configuration module for the SCARE Unified Dashboard API.
This module handles database connection configuration and validation.
"""
import os
import re
import sys
import time
import socket
import logging
import traceback
from urllib.parse import urlparse, parse_qs
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_config")

def mask_password(url):
    """
    Mask the password in a database URL for safe logging
    """
    if not url:
        return None
    
    try:
        # Use regex to replace password in URL
        masked_url = re.sub(r'(postgresql://[^:]+:)([^@]+)(@.*)', r'\1****\3', url)
        return masked_url
    except Exception as e:
        logger.error(f"Error masking password in URL: {e}")
        # Return a completely masked URL if there's an error
        return "postgresql://****:****@****:****/*****"

def validate_database_url(url):
    """
    Validate the format and components of a database URL
    Returns (is_valid, error_message)
    """
    if not url:
        return False, "Database URL is empty or None"
    
    try:
        # Check if URL starts with postgresql://
        if not url.startswith("postgresql://"):
            return False, "Database URL must start with postgresql://"
        
        # Parse the URL
        parsed = urlparse(url)
        
        # Check required components
        if not parsed.hostname:
            return False, "Database URL is missing hostname"
        if not parsed.username:
            return False, "Database URL is missing username"
        if not parsed.password:
            return False, "Database URL is missing password"
        if not parsed.path or parsed.path == '/':
            return False, "Database URL is missing database name"
        
        # Validate port if present
        if parsed.port and (parsed.port < 1 or parsed.port > 65535):
            return False, f"Invalid port number: {parsed.port}"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating database URL: {e}")
        return False, f"Error validating database URL: {str(e)}"

def test_database_connection(hostname, port, timeout=5):
    """
    Test TCP connection to the database server
    Returns (is_connected, error_message)
    """
    logger.info(f"Testing TCP connection to database server at {hostname}:{port}")
    
    # Skip hostname resolution test if we're in Railway and using internal hostnames
    if os.environ.get("RAILWAY_ENVIRONMENT_NAME") and (
        "railway.internal" in hostname or 
        "postgres.railway.internal" == hostname or
        hostname.endswith(".up.railway.app")
    ):
        logger.info(f"Skipping connection test for Railway internal hostname: {hostname}")
        return True, None
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Resolve hostname to IP address
        try:
            ip_address = socket.gethostbyname(hostname)
            logger.info(f"Resolved {hostname} to {ip_address}")
        except socket.gaierror:
            logger.error(f"Hostname resolution failed for {hostname}")
            return False, f"Hostname resolution failed for {hostname}"
        
        # Try to connect
        result = sock.connect_ex((ip_address, port))
        sock.close()
        
        if result == 0:
            logger.info(f"Successfully connected to {hostname}:{port}")
            return True, None
        else:
            error_msg = f"Connection failed with error code {result}"
            logger.error(error_msg)
            return False, error_msg
            
    except socket.timeout:
        logger.error(f"Connection to {hostname}:{port} timed out after {timeout} seconds")
        return False, f"Connection timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"Error testing connection to {hostname}:{port}: {str(e)}")
        return False, str(e)

def add_ssl_params_if_needed(url):
    """
    Add SSL parameters to the database URL if needed
    """
    if not url:
        return url
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Check if this is a Railway environment
        is_railway = os.environ.get("RAILWAY_ENVIRONMENT_NAME") is not None
        
        # Check if this is a Railway internal connection or public connection
        is_railway_internal = parsed.hostname and "railway.internal" in parsed.hostname
        is_railway_public = parsed.hostname and ".up.railway.app" in parsed.hostname
        
        # Parse existing query parameters
        query_params = parse_qs(parsed.query)
        
        # If it's a Railway connection and no SSL mode is specified, add it
        if (is_railway or is_railway_internal or is_railway_public) and "sslmode" not in query_params:
            # Add SSL mode parameter
            if parsed.query:
                new_url = f"{url}&sslmode=require"
            else:
                new_url = f"{url}?sslmode=require"
            
            logger.info("Added SSL parameters to database URL for Railway connection")
            return new_url
        
        return url
    except Exception as e:
        logger.error(f"Error adding SSL parameters to URL: {e}")
        return url

def is_railway_environment():
    """Check if we're running in Railway environment."""
    return os.environ.get("RAILWAY_ENVIRONMENT_NAME") is not None or os.environ.get("RAILWAY_ENVIRONMENT") is not None

def get_database_url(test_connection=False):
    """Get the database URL from environment variables"""
    # Check if we're running in Railway environment
    in_railway = is_railway_environment()
    logger.info(f"Running in Railway environment: {in_railway}")
    
    # CRITICAL FIX: First get the full DATABASE_URL to extract password
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        masked_url = mask_password(database_url)
        logger.info(f"Found DATABASE_URL: {masked_url}")
        
        # Extract password from DATABASE_URL
        try:
            parsed = urlparse(database_url)
            username = parsed.username or "postgres"
            password = parsed.password
            logger.info(f"Extracted username: {username}")
            if password:
                logger.info("Successfully extracted password from DATABASE_URL")
            else:
                logger.warning("No password found in DATABASE_URL")
        except Exception as e:
            logger.error(f"Error parsing DATABASE_URL: {e}")
            username = "postgres"
            password = ""
    else:
        username = "postgres"
        password = ""
        logger.warning("No DATABASE_URL found")
    
    if in_railway:
        # CRITICAL FIX - Use extracted password in internal URL
        logger.info("CRITICAL FIX: Using extracted credentials with Railway internal connection")
        
        # Use extracted credentials or fall back to environment variables
        pg_user = username or os.getenv("POSTGRES_USER") or os.getenv("PGUSER") or "postgres"
        pg_password = password or os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD", "")
        pg_database = os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE") or "railway"
        
        # Force internal hostname but use extracted credentials
        internal_url = f"postgresql://{pg_user}:{pg_password}@postgres.railway.internal:5432/{pg_database}?sslmode=require"
        masked_url = mask_password(internal_url)
        logger.info(f"Using internal URL with extracted credentials: {masked_url}")
        return internal_url
    
    # Local development - use DATABASE_URL or fall back to localhost
    if not database_url:
        default_url = "postgresql://postgres:postgres@localhost:5432/postgres"
        logger.warning(f"No DATABASE_URL found. Using default local URL: {default_url}")
        return default_url
    
    # Add SSL parameters if needed
    database_url = add_ssl_params_if_needed(database_url)
    masked_url = mask_password(database_url)
    logger.info(f"Using database URL: {masked_url}")
    return database_url

def create_engine_with_retry(database_url, **kwargs):
    """
    Create a SQLAlchemy engine with retry logic
    
    Args:
        database_url: The database URL to connect to
        **kwargs: Additional arguments to pass to create_engine
        
    Returns:
        SQLAlchemy engine
    """
    # Ensure connect_args is present
    if "connect_args" not in kwargs:
        kwargs["connect_args"] = {}
    
    # Set application name for easier identification in PostgreSQL logs
    kwargs["connect_args"]["application_name"] = "SCARE Unified Dashboard"
    
    # Set connect timeout if not already set - use 60 seconds to allow for slow networks
    if "connect_timeout" not in kwargs["connect_args"]:
        kwargs["connect_args"]["connect_timeout"] = 60
    
    # Add keepalives to prevent connection closures
    if "keepalives" not in kwargs["connect_args"]:
        kwargs["connect_args"]["keepalives"] = 1
        kwargs["connect_args"]["keepalives_idle"] = 30
        kwargs["connect_args"]["keepalives_interval"] = 10
        kwargs["connect_args"]["keepalives_count"] = 5
    
    # Force IPv4 connectivity which is more reliable with Railway proxy
    if "options" not in kwargs["connect_args"]:
        kwargs["connect_args"]["options"] = "-c statement_timeout=60000 -c prefer_ipv4=true"
    
    # Set SSL mode to prefer if not already set
    # This allows SSL connections but doesn't require them
    if "sslmode" not in kwargs["connect_args"]:
        kwargs["connect_args"]["sslmode"] = "prefer"
    
    # Add pool settings for better connection handling
    if "pool_pre_ping" not in kwargs:
        kwargs["pool_pre_ping"] = True
    if "pool_recycle" not in kwargs:
        kwargs["pool_recycle"] = 300  # Recycle connections after 5 minutes
    if "pool_timeout" not in kwargs:
        kwargs["pool_timeout"] = 30  # Wait up to 30 seconds for a connection
    
    # Log connection parameters for debugging
    masked_url = mask_password(database_url)
    logger.info(f"Creating SQLAlchemy engine with URL: {masked_url}")
    logger.info(f"Connection arguments: {kwargs}")
    
    # Extract hostname for logging
    hostname = None
    try:
        parsed = urlparse(database_url)
        hostname = parsed.hostname
        port = parsed.port
        logger.info(f"Connecting to host: {hostname}:{port}")
    except Exception as e:
        logger.error(f"Error parsing URL: {e}")
    
    # Create engine
    try:
        engine = create_engine(database_url, **kwargs)
        return engine
    except Exception as e:
        logger.error(f"Error creating engine: {e}")
        raise

def get_engine_args():
    """
    Get additional arguments for SQLAlchemy engine creation
    """
    return {
        "connect_args": {
            "connect_timeout": 60,
            "application_name": "SCARE Unified Dashboard API",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "options": "-c statement_timeout=60000"
        },
        "pool_pre_ping": True,
        "pool_recycle": 300,  # Recycle connections after 5 minutes
        "pool_timeout": 30,
        "pool_size": 5,
        "max_overflow": 10
    }

# For testing
if __name__ == "__main__":
    # Test the database configuration
    database_url = get_database_url()
    if database_url:
        print(f"Database URL: {mask_password(database_url)}")
    else:
        print("No database URL available")
