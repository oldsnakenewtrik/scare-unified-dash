"""
Minimal FastAPI app to test CORS functionality
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
import datetime

# Create a minimal app
app = FastAPI(title="CORS Test App")

# For debugging
print("=====================================================")
print("INITIALIZING MINIMAL TEST APP")
print("=====================================================")
print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("PYTHONPATH:", os.environ.get("PYTHONPATH", "Not set"))
print("PORT:", os.environ.get("PORT", "Not set"))

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
print("CORS middleware configured")

# Health check endpoint - both with and without /api prefix
@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "status": "ok", 
        "message": "CORS test app is running",
        "timestamp": datetime.datetime.now().isoformat()
    }

# CORS test endpoint - both with and without /api prefix
@app.get("/cors-test")
@app.get("/api/cors-test")
async def cors_test(request: Request):
    try:
        origin = request.headers.get("origin", "No origin provided")
        
        # Create a response with CORS headers
        response = JSONResponse(
            content={
                "status": "ok",
                "message": "CORS test endpoint",
                "timestamp": datetime.datetime.now().isoformat(),
                "request_origin": origin,
                "origins_allowed": origins,
                "environment_vars": {
                    "PORT": os.environ.get("PORT", "Not set"),
                    "DATABASE_URL": os.environ.get("DATABASE_URL", "Not set"),
                    "PYTHONPATH": os.environ.get("PYTHONPATH", "Not set"),
                }
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

# Handle all OPTIONS requests
@app.options("/{path:path}")
async def options_handler(path: str):
    return {"status": "ok"}

# Hello world endpoint
@app.get("/")
async def root():
    return {
        "message": "CORS test app is running",
        "endpoints": ["/api/health", "/api/cors-test", "/health", "/cors-test"],
        "timestamp": datetime.datetime.now().isoformat()
    }

# For direct execution
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
