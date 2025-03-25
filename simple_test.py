"""
Simplified test script to check a single endpoint
"""
import requests
import json

API_URL = "https://scare-unified-dash-production.up.railway.app"
TEST_ENDPOINT = "/api/test"

def test_endpoint():
    url = f"{API_URL}{TEST_ENDPOINT}"
    print(f"Testing: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
            print("\n✅ Test endpoint is working!")
            return True
        else:
            print(f"❌ Failed with status: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_endpoint()
