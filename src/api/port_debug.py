"""
Port debugging utility for Railway deployment
This script will print the port configuration and environment variables
"""

import os
import sys
import json

def main():
    """Print port configuration and environment variables"""
    print("=" * 50)
    print("PORT CONFIGURATION DEBUG")
    print("=" * 50)
    
    # Get PORT environment variable
    port = os.environ.get("PORT", "Not set")
    print(f"PORT environment variable: {port}")
    
    # Get all environment variables
    env_vars = {k: v for k, v in os.environ.items() if k.startswith("PORT") or k.startswith("RAILWAY")}
    print(f"Environment variables related to port or Railway: {json.dumps(env_vars, indent=2)}")
    
    # Check if we can access the port from sys.argv
    if len(sys.argv) > 1:
        print(f"Command line arguments: {sys.argv[1:]}")
    else:
        print("No command line arguments provided")
    
    print("=" * 50)
    print("END PORT CONFIGURATION DEBUG")
    print("=" * 50)

if __name__ == "__main__":
    main()
