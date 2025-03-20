"""
Simple script to test CORS headers on a local FastAPI instance.
"""
import requests
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_cors")

def test_cors(base_url, origin="https://front-production-f6e6.up.railway.app"):
    """Test CORS headers on a FastAPI instance."""
    test_endpoints = [
        "/api/health",
        "/cors-test",
        "/api/campaigns/metrics",
        "/api/campaign-mappings"
    ]
    
    logger.info(f"Testing CORS headers on {base_url} with origin {origin}")
    
    for endpoint in test_endpoints:
        url = f"{base_url}{endpoint}"
        
        # Test OPTIONS request (preflight)
        try:
            logger.info(f"Testing OPTIONS request to {url}")
            headers = {
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type"
            }
            response = requests.options(url, headers=headers, timeout=5)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if "access-control-allow-origin" in response.headers:
                logger.info(f"✅ CORS headers present for OPTIONS on {endpoint}")
            else:
                logger.error(f"❌ No CORS headers for OPTIONS on {endpoint}")
        except Exception as e:
            logger.error(f"❌ Error testing OPTIONS on {endpoint}: {str(e)}")
        
        # Test GET request
        try:
            logger.info(f"Testing GET request to {url}")
            headers = {"Origin": origin}
            response = requests.get(url, headers=headers, timeout=5)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if "access-control-allow-origin" in response.headers:
                logger.info(f"✅ CORS headers present for GET on {endpoint}")
            else:
                logger.error(f"❌ No CORS headers for GET on {endpoint}")
        except Exception as e:
            logger.error(f"❌ Error testing GET on {endpoint}: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_cors.py <base_url> [origin]")
        print("Example: python test_cors.py http://localhost:5000 https://example.com")
        sys.exit(1)
    
    base_url = sys.argv[1]
    origin = sys.argv[2] if len(sys.argv) > 2 else "https://front-production-f6e6.up.railway.app"
    
    test_cors(base_url, origin)
