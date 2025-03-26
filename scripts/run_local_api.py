"""
Run the SCARE Unified Dashboard API locally with the correct database configuration.
This script sets up the environment properly for local development.
"""
import os
import sys
import uvicorn
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("run_local_api")

def main():
    """Run the API locally with the correct configuration"""
    # Load environment variables from .env.local first
    local_env_path = os.path.join(os.path.dirname(__file__), '.env.local')
    if os.path.exists(local_env_path):
        logger.info(f"Loading environment from {local_env_path}")
        load_dotenv(local_env_path)
    else:
        logger.warning("No .env.local file found")
    
    # Then load regular .env file as fallback
    load_dotenv()
    
    # Set up external database URL if needed
    if "DATABASE_URL" in os.environ and "railway.internal" in os.environ["DATABASE_URL"]:
        logger.warning("Detected Railway internal URL in DATABASE_URL")
        
        # Set up external URL
        external_url = "postgresql://postgres:HGnALEQyXYobjgWixRVpnfQBVXcfTXoF@nozomi.proxy.rlwy.net:11923/railway"
        logger.info(f"Setting EXTERNAL_DATABASE_URL for local development")
        os.environ["EXTERNAL_DATABASE_URL"] = external_url
    
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    
    # Print debug information
    logger.info(f"Starting server on port {port}")
    logger.info("Environment variables:")
    for key, value in os.environ.items():
        if "PASSWORD" in key.upper() or "SECRET" in key.upper() or "KEY" in key.upper():
            logger.info(f"{key}: [REDACTED]")
        elif key.startswith("DATABASE") or key.startswith("RAILWAY"):
            logger.info(f"{key}: {value}")
    
    # Run the application
    logger.info("Starting API server...")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
