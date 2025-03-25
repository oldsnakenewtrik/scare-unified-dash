"""
Test script to verify FastAPI routing before deployment.
This script helps diagnose routing issues with FastAPI applications.
"""
import requests
import json
import sys
import os
from datetime import datetime

# Change this to your local or Railway API URL
# LOCAL_API_URL = "http://localhost:5000"
RAILWAY_API_URL = "https://scare-unified-dash-production.up.railway.app"

# Set the API URL to test
API_URL = RAILWAY_API_URL

# List of endpoints to test
ENDPOINTS = [
    "/api/test",  # Our new test endpoint
    "/api/campaigns-hierarchical",
    "/api/campaign-mappings",
    "/api/unmapped-campaigns",
    "/api/campaign-metrics",
    "/health",
]

def print_header(text):
    """Print a header with the given text."""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80)

def print_response(endpoint, response):
    """Print response details for the given endpoint."""
    print(f"\n--- {endpoint} ---")
    print(f"Status: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    try:
        data = response.json()
        print("\nResponse (first 300 chars):")
        json_str = json.dumps(data, indent=2)
        print(json_str[:300] + "..." if len(json_str) > 300 else json_str)
        
        # Check for error patterns
        if isinstance(data, dict) and "error" in data:
            print(f"\n⚠️ ERROR DETECTED: {data.get('error')}")
    except Exception as e:
        print("\nNot JSON data")
        print(response.text[:300])

def test_api_endpoints():
    """Test all API endpoints and print results."""
    print_header("API ROUTING TEST")
    print(f"Testing API at: {API_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    
    results = {"success": 0, "error": 0, "total": len(ENDPOINTS)}
    
    for endpoint in ENDPOINTS:
        url = f"{API_URL}{endpoint}"
        print(f"\nTesting: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print_response(endpoint, response)
            
            # Check if response indicates an error
            if response.status_code >= 400:
                print("❌ FAILED: HTTP error status code")
                results["error"] += 1
            elif "error" in response.text.lower() and "not found" in response.text.lower():
                print("❌ FAILED: Response contains error message")
                results["error"] += 1
            else:
                print("✅ SUCCESS")
                results["success"] += 1
                
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            results["error"] += 1
    
    # Print summary
    print_header("TEST SUMMARY")
    print(f"Total endpoints tested: {results['total']}")
    print(f"Successful: {results['success']}")
    print(f"Failed: {results['error']}")
    
    if results["error"] == 0:
        print("\n🎉 All endpoints are working correctly!")
    else:
        print(f"\n⚠️ {results['error']} endpoints failed the test.")
        
    # Return exit code based on results
    return 1 if results["error"] > 0 else 0
        
if __name__ == "__main__":
    sys.exit(test_api_endpoints())
