"""
Database configuration module for SCARE Unified Dashboard.
Handles different database connection strings for local development and Railway deployment.
"""
import os
import sys
import logging
import socket
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_config")

def is_railway_environment():
    """Check if we're running in Railway environment"""
    return os.getenv("RAILWAY_PROJECT_ID") is not None or os.getenv("RAILWAY_ENVIRONMENT") is not None

def get_database_url():
    """
    Get the appropriate database URL based on the environment.
    For local development, use the external connection string.
    For Railway deployment, use the public connection string.
    """
    # Load environment variables - try .env.local first for local development
    local_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env.local')
    if os.path.exists(local_env_path):
        logger.info(f"Loading environment from {local_env_path}")
        load_dotenv(local_env_path)
    
    # Then load regular .env file as fallback
    load_dotenv()
    
    # Check if we're running in Railway
    in_railway = is_railway_environment()
    logger.info(f"Running in Railway environment: {in_railway}")
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    # Important: Always replace railway.internal with the public hostname
    # This is needed because private networking appears to be failing
    if database_url and "railway.internal" in database_url:
        # Extract the public hostname from PGHOST or DATABASE_URL
        pg_host = os.getenv("PGHOST")
        if pg_host and "railway.app" in pg_host:
            # Replace the internal hostname with the public one
            database_url = database_url.replace("postgres.railway.internal", pg_host)
            logger.info("Replaced internal Railway hostname with public hostname")
        else:
            # If we can't find the public hostname, try to parse it from DATABASE_URL
            # The format is typically postgresql://user:pass@hostname:port/dbname
            try:
                # Get the public hostname from Railway environment variables
                public_hostname = os.getenv("RAILWAY_PUBLIC_DOMAIN")
                if public_hostname:
                    database_url = database_url.replace("postgres.railway.internal", public_hostname)
                    logger.info(f"Using public hostname from RAILWAY_PUBLIC_DOMAIN: {public_hostname}")
                else:
                    # If all else fails, use a hardcoded public URL from our .env.local
                    external_url = os.getenv("EXTERNAL_DATABASE_URL")
                    if external_url:
                        database_url = external_url
                        logger.info("Using EXTERNAL_DATABASE_URL as fallback")
            except Exception as e:
                logger.error(f"Error parsing database URL: {str(e)}")
    
    # Log the final URL (with masked password)
    masked_url = mask_password(database_url) if database_url else "None"
    logger.info(f"Using database URL: {masked_url}")
    
    return database_url

def mask_password(url):
    """Mask the password in a database URL for logging"""
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

# For testing
if __name__ == "__main__":
    url = get_database_url()
    print(f"Database URL: {mask_password(url)}")
