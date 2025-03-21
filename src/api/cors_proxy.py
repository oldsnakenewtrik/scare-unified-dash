"""
A simple CORS proxy for the SCARE Unified Dashboard API.
This file will directly wrap the FastAPI application with CORS headers.
"""
import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cors_proxy")

# Import the main FastAPI app
try:
    from src.api.main import app as main_app
    logger.info("Successfully imported the main FastAPI app from src.api.main")
except ImportError:
    try:
        # Try a different import path
        import sys
        sys.path.append(os.getcwd())
        from src.api.main import app as main_app
        logger.info("Successfully imported the main FastAPI app using a modified path")
    except ImportError as e:
        logger.error(f"Failed to import the main FastAPI app: {e}")
        # Create a dummy app as a fallback
        main_app = FastAPI()
        
        @main_app.get("/")
        def root():
            return {"message": "CORS proxy is running, but the main app failed to load"}

# Create a new FastAPI app that will wrap the main app
app = FastAPI(title="CORS Proxy for SCARE Unified Dashboard API")

# Configure CORS to allow specific origins
origins = ["*"]  # Allow all origins for testing

# Add CORS middleware to the proxy app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add a middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Log the request origin for debugging
    origin = request.headers.get("origin", "No origin")
    logger.info(f"Request origin: {origin}")
    
    try:
        # Process the request through the main app
        response = await call_next(request)
        
        # Add CORS headers to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"  # Allow all origins
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"  # Cache preflight response for 24 hours
        
        logger.info(f"Response: {response.status_code}")
        logger.info(f"CORS headers set: {response.headers.get('Access-Control-Allow-Origin')}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        
        # Return a generic error response
        response = Response(content=str(e), status_code=500)
        
        # Set CORS headers for all origins
        response.headers["Access-Control-Allow-Origin"] = "*"  # Allow all origins
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

# Add a health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Add WebSocket support
try:
    from src.api.websocket import add_websocket_endpoints
    app = add_websocket_endpoints(app)
    logger.info("WebSocket support added successfully")
except ImportError as e:
    logger.error(f"Failed to add WebSocket support: {e}")

# Mount the main app
app.mount("/", main_app)

# Handle OPTIONS requests explicitly
@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    logger.info(f"Handling OPTIONS request for /{path}")
    
    # Return an empty response with CORS headers
    response = Response()
    
    # Set CORS headers for all origins
    response.headers["Access-Control-Allow-Origin"] = "*"  # Allow all origins
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "86400"  # Cache preflight response for 24 hours
    return response

# Entry point for running the proxy directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting CORS proxy on port {port}")
    uvicorn.run("cors_proxy:app", host="0.0.0.0", port=port, reload=False)
