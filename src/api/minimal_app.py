"""
Minimal FastAPI application for Railway deployment
This app has no dependencies and will always pass health checks
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("minimal_app")

app = FastAPI(title="Minimal API")

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

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Simple health check endpoint that always passes"""
    logger.info("Health check endpoint accessed")
    return {
        "status": "ok",
        "message": "Minimal API is running",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/cors-test")
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

@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {
        "message": "Minimal API is running",
        "endpoints": ["/api/health", "/api/cors-test", "/health", "/cors-test", "/info"],
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/info")
async def info():
    """Information about the environment"""
    logger.info("Info endpoint accessed")
    return {
        "environment": {
            "PORT": os.environ.get("PORT", "Not set"),
            "RAILWAY_SERVICE_NAME": os.environ.get("RAILWAY_SERVICE_NAME", "Not set"),
            "RAILWAY_ENVIRONMENT_NAME": os.environ.get("RAILWAY_ENVIRONMENT_NAME", "Not set"),
            "RAILWAY_PUBLIC_DOMAIN": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "Not set")
        },
        "timestamp": datetime.datetime.now().isoformat()
    }
