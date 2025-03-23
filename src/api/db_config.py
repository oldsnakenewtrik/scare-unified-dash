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
    For Railway deployment, use the internal connection string.
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
    
    # If we're in Railway, use the DATABASE_URL directly without modification
    if in_railway:
        logger.info("Using Railway environment DATABASE_URL")
        if not database_url:
            logger.error("No DATABASE_URL found in Railway environment")
        return database_url
    
    # For local development
    if not in_railway:
        logger.info("Running in local development environment")
        
        # If DATABASE_URL contains railway.internal, try to use an external URL
        if database_url and "railway.internal" in database_url:
            logger.warning("Detected Railway internal URL while running locally")
            
            # Try to use EXTERNAL_DATABASE_URL if available
            external_url = os.getenv("EXTERNAL_DATABASE_URL")
            if external_url:
                logger.info("Using external database URL from EXTERNAL_DATABASE_URL")
                database_url = external_url
            else:
                # Use the public networking URL
                public_url = "postgresql://postgres:HGnALEQyXYobjgWixRVpnfQBVXcfTXoF@postgres-production-07fa.up.railway.app:5432/railway"
                logger.info(f"Using public networking URL: {mask_password(public_url)}")
                database_url = public_url
    
    # If no DATABASE_URL is found, use a default for local development
    if not database_url:
        default_url = "postgresql://postgres:HGnALEQyXYobjgWixRVpnfQBVXcfTXoF@postgres-production-07fa.up.railway.app:5432/railway"
        logger.warning(f"No DATABASE_URL found, using default: {mask_password(default_url)}")
        database_url = default_url
    
    # Log the database URL (masked) for debugging
    logger.info(f"Using database URL: {mask_password(database_url)}")
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
