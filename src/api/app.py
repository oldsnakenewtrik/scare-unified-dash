import os
import sys
import uvicorn
from main import app

def main():
    """
    Main entry point for the application.
    This ensures that the application uses the PORT environment variable provided by Railway.
    """
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    
    # Print debug information
    print(f"Starting server on port {port}")
    print(f"Environment variables:")
    for key, value in os.environ.items():
        if "PASSWORD" in key.upper() or "SECRET" in key.upper() or "KEY" in key.upper():
            print(f"{key}: [REDACTED]")
        else:
            print(f"{key}: {value}")
    
    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
