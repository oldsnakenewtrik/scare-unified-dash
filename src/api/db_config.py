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
    return os.getenv("RAILWAY_PROJECT_ID") is not None

def is_host_reachable(host, port, timeout=3):
    """Check if a host is reachable on a specific port"""
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

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
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    # If we're running locally and the DATABASE_URL contains railway.internal,
    # try to use the external connection string instead
    if not in_railway and database_url and "railway.internal" in database_url:
        logger.warning("Detected Railway internal URL while running locally")
        
        # Try different connection options
        connection_options = [
            # Option 1: Use EXTERNAL_DATABASE_URL if available
            os.getenv("EXTERNAL_DATABASE_URL"),
            
            # Option 2: Use the public networking URL
            "postgresql://postgres:HGnALEQyXYobjgWixRVpnfQBVXcfTXoF@postgres-production-07fa.up.railway.app:5432/railway",
            
            # Option 3: Use the proxy URL
            "postgresql://postgres:HGnALEQyXYobjgWixRVpnfQBVXcfTXoF@nozomi.proxy.rlwy.net:11923/railway"
        ]
        
        # Filter out None values
        connection_options = [url for url in connection_options if url]
        
        # Try each connection option
        for option in connection_options:
            try:
                # Extract host and port for reachability test
                parts = option.split("://")[1].split("@")[1].split("/")[0]
                if ":" in parts:
                    host, port = parts.split(":")
                    port = int(port)
                else:
                    host = parts
                    port = 5432  # Default PostgreSQL port
                
                # Check if the host is reachable
                if is_host_reachable(host, port):
                    logger.info(f"Found reachable database at {host}:{port}")
                    database_url = option
                    break
            except Exception as e:
                logger.warning(f"Error checking connection option: {e}")
        
        if database_url and "railway.internal" in database_url:
            logger.warning("Could not find a working external connection, using original URL")
    
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
