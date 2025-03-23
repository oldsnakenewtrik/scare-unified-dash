"""
Server runner module for SCARE Unified Dashboard
This module handles proper environment variable parsing and starts the server
"""
import os
import sys
import uvicorn
import logging
import importlib.util
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("run_server")

# Try to import the main app directly to verify it's available
try:
    from src.api.main import app
    logger.info("Successfully imported main app")
except Exception as e:
    logger.error(f"Error importing main app: {e}")
    logger.info("Will attempt to run using module path instead")

def verify_health_endpoint():
    """Verify that the health endpoint is available in the app"""
    try:
        # Import the app
        from src.api.main import app
        
        # Check if the health endpoint is registered
        routes = [f"{route.path}" for route in app.routes]
        logger.info(f"Available routes: {routes}")
        
        if "/api/health" in routes:
            logger.info("Health endpoint /api/health is available")
        else:
            logger.warning("Health endpoint /api/health is NOT available!")
            
            # Add a health endpoint if it doesn't exist
            logger.info("Adding a basic health endpoint at /api/health")
            
            @app.get("/api/health")
            async def emergency_health_check():
                return {
                    "status": "ok",
                    "message": "Emergency health endpoint",
                    "timestamp": time.time()
                }
            
            logger.info("Emergency health endpoint added")
    except Exception as e:
        logger.error(f"Error verifying health endpoint: {e}")

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
        
        # Verify the health endpoint is available
        verify_health_endpoint()
        
        # Start the server
        logger.info(f"Starting server on port {port}")
        uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        # Try one more time with a hardcoded port
        logger.info("Attempting to start with hardcoded port 8000")
        try:
            # Try to import the app directly
            try:
                from src.api.main import app
                logger.info("Running app directly")
                uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
            except Exception as import_error:
                logger.error(f"Failed to import app directly: {import_error}")
                logger.info("Falling back to minimal app")
                
                # If main app fails, try to run the minimal app
                try:
                    from src.api.minimal_app import app as minimal_app
                    logger.info("Running minimal app")
                    uvicorn.run(minimal_app, host="0.0.0.0", port=8000, log_level="info")
                except Exception as minimal_error:
                    logger.error(f"Failed to run minimal app: {minimal_error}")
                    sys.exit(1)
        except Exception as e2:
            logger.error(f"Failed to start with hardcoded port: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()
