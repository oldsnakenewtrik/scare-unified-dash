"""
Ultra-minimal FastAPI app to debug Railway deployment
"""
from fastapi import FastAPI
import uvicorn
import os
import sys

# Create a bare-bones FastAPI app
app = FastAPI()

# Print environment info
print("=====================================================")
print("STARTING ULTRA-MINIMAL APP")
print("=====================================================")
print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("PYTHONPATH:", os.environ.get("PYTHONPATH", "Not set"))
print("PORT:", os.environ.get("PORT", "Not set"))
print("Environment variables:", dict(os.environ))

@app.get("/")
async def root():
    return {"message": "Hello from super_simple.py"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
