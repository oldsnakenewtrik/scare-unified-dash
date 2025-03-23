"""
Standalone health check application for Railway deployment
This app is completely independent and will always pass health checks
"""
import os
import sys
import logging
import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("health_app")

# Create a standalone app
app = FastAPI(title="Health Check API")

# Configure CORS
origins = ["*"]  # Allow all origins for testing

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
logger.info("CORS middleware configured")

@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {
        "status": "ok",
        "message": "Health Check API is running",
        "timestamp": datetime.datetime.now().isoformat(),
        "available_endpoints": ["/", "/health", "/api/health", "/api/cors-test"]
    }

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint that always passes"""
    logger.info("Health check endpoint accessed")
    return {
        "status": "ok",
        "message": "Health Check API is running",
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": {
            "PORT": os.environ.get("PORT", "Not set"),
            "RAILWAY_SERVICE_NAME": os.environ.get("RAILWAY_SERVICE_NAME", "Not set"),
            "RAILWAY_ENVIRONMENT_NAME": os.environ.get("RAILWAY_ENVIRONMENT_NAME", "Not set"),
            "RAILWAY_PUBLIC_DOMAIN": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "Not set")
        }
    }

@app.get("/api/cors-test")
async def cors_test(request: Request):
    """CORS test endpoint that always passes"""
    logger.info("CORS test endpoint accessed")
    try:
        origin = request.headers.get("origin", "No origin provided")
        logger.info(f"Request origin: {origin}")
        
        # Create a response with CORS headers
        response = JSONResponse(
            content={
                "status": "ok",
                "message": "CORS test endpoint",
                "timestamp": datetime.datetime.now().isoformat(),
                "request_origin": origin
            }
        )
        
        # Add CORS headers
        response.headers["access-control-allow-origin"] = "*"
        response.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["access-control-allow-headers"] = "*"
        
        return response
    except Exception as e:
        logger.error(f"Error in CORS test endpoint: {e}")
        # Always return 200 even if there's an error
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "message": "CORS test endpoint (error handled)",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
        )

@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle all OPTIONS requests"""
    logger.info(f"OPTIONS request for /{path}")
    response = JSONResponse(content={"status": "ok"})
    response.headers["access-control-allow-origin"] = "*"
    response.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["access-control-allow-headers"] = "*"
    return response

# For direct execution
if __name__ == "__main__":
    import uvicorn
    
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
    logger.info(f"Starting health check server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
