"""
Minimal FastAPI app to test CORS functionality
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

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

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "message": "CORS test app is running"}

# CORS test endpoint
@app.get("/cors-test")
async def cors_test():
    return {
        "status": "ok", 
        "message": "CORS headers should be present in this response",
        "origins_allowed": origins,
        "environment_vars": {
            "PORT": os.environ.get("PORT", "Not set"),
            "DATABASE_URL": os.environ.get("DATABASE_URL", "Not set"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", "Not set"),
        }
    }

# Handle all OPTIONS requests
@app.options("/{path:path}")
async def options_handler(path: str):
    print(f"Handling OPTIONS request for /{path}")
    return {}

# Hello world endpoint
@app.get("/")
async def root():
    return {"message": "Hello World from test_app.py"}

# For direct execution
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("test_app:app", host="0.0.0.0", port=port)
