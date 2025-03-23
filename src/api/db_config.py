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
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Try to connect
        start_time = time.time()
        result = sock.connect_ex((hostname, port))
        elapsed_time = time.time() - start_time
        
        # Close socket
        sock.close()
        
        if result == 0:
            logger.info(f"TCP connection successful (took {elapsed_time:.2f} seconds)")
            return True, None
        else:
            error_msg = f"TCP connection failed with error code {result} (took {elapsed_time:.2f} seconds)"
            logger.error(error_msg)
            return False, error_msg
    except socket.gaierror:
        logger.error(f"Hostname resolution failed for {hostname}")
        return False, f"Hostname resolution failed for {hostname}"
    except socket.timeout:
        logger.error(f"Connection timed out after {timeout} seconds")
        return False, f"Connection timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"TCP connection error: {str(e)}")
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
        
        # Check if this is a Railway internal connection
        is_railway_internal = parsed.hostname and "railway.internal" in parsed.hostname
        
        # Parse existing query parameters
        query_params = parse_qs(parsed.query)
        
        # If it's a Railway internal connection, we may need to add SSL parameters
        if is_railway_internal and "sslmode" not in query_params:
            # Add SSL mode parameter
            if parsed.query:
                new_url = f"{url}&sslmode=require"
            else:
                new_url = f"{url}?sslmode=require"
            
            logger.info("Added SSL parameters to database URL for Railway internal connection")
            return new_url
        
        return url
    except Exception as e:
        logger.error(f"Error adding SSL parameters to URL: {e}")
        return url

def get_database_url(test_connection=True):
    """
    Get the database URL from environment variables
    Returns the database URL or None if not available
    """
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
    
    # Validate the URL
    is_valid, error = validate_database_url(database_url)
    if not is_valid:
        logger.error(f"Invalid database URL: {error}")
        return None
    
    # Add SSL parameters if needed
    database_url = add_ssl_params_if_needed(database_url)
    
    # Test the connection if requested
    if test_connection:
        try:
            # Parse the URL
            parsed = urlparse(database_url)
            hostname = parsed.hostname
            port = parsed.port or 5432
            
            # Test TCP connection
            is_connected, error = test_database_connection(hostname, port)
            if not is_connected:
                logger.error(f"Database connection test failed: {error}")
                # Return the URL anyway, as the application may retry later
        except Exception as e:
            logger.error(f"Error testing database connection: {e}")
    
    return database_url

def get_engine_args():
    """
    Get additional arguments for SQLAlchemy engine creation
    """
    return {
        "connect_args": {
            "connect_timeout": 10,
            "application_name": "SCARE Unified Dashboard API"
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
