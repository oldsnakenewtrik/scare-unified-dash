"""
Server runner module for SCARE Unified Dashboard
This module handles proper environment variable parsing and starts the server
"""
import os
import sys
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("run_server")

def main():
    """Main entry point for the application"""
    try:
        # Get the port from environment variable, with fallback to 8000
        port_str = os.environ.get("PORT")
        
        # Log the raw PORT environment variable for debugging
        logger.info(f"Raw PORT environment variable: {port_str!r}")
        
        # Parse the port, with fallback to 8000
        if port_str is None:
            port = 8000
            logger.info(f"PORT environment variable not set, using default: {port}")
        else:
            try:
                port = int(port_str)
                logger.info(f"Using PORT from environment: {port}")
            except ValueError:
                # If PORT is not a valid integer, use default
                port = 8000
                logger.warning(f"Invalid PORT value: {port_str!r}, using default: {port}")
        
        # Log all environment variables for debugging (excluding sensitive ones)
        safe_env = {k: v for k, v in os.environ.items() 
                   if not any(secret in k.lower() for secret in ['password', 'secret', 'key', 'token'])}
        logger.info(f"Environment variables: {safe_env}")
        
        # Start the server
        logger.info(f"Starting server on port {port}")
        uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        # Try one more time with a hardcoded port
        logger.info("Attempting to start with hardcoded port 8000")
        try:
            uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, log_level="info")
        except Exception as e2:
            logger.error(f"Failed to start with hardcoded port: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()
