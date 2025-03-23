"""
Minimal FastAPI application for Railway deployment
This app has no dependencies and will always pass health checks
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import datetime
import os

app = FastAPI(title="Minimal API")

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint that always passes"""
    return {
        "status": "ok",
        "message": "Minimal API is running",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/api/cors-test")
async def cors_test(request: Request):
    """CORS test endpoint that always passes"""
    try:
        origin = request.headers.get("origin", "No origin provided")
        
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Minimal API is running",
        "endpoints": ["/api/health", "/api/cors-test", "/info"],
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/info")
async def info():
    """Information about the environment"""
    return {
        "environment": {
            "PORT": os.environ.get("PORT", "Not set"),
            "RAILWAY_SERVICE_NAME": os.environ.get("RAILWAY_SERVICE_NAME", "Not set"),
            "RAILWAY_ENVIRONMENT_NAME": os.environ.get("RAILWAY_ENVIRONMENT_NAME", "Not set"),
            "RAILWAY_PUBLIC_DOMAIN": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "Not set")
        },
        "timestamp": datetime.datetime.now().isoformat()
    }
