"""
Script to check API endpoints and verify campaign data.
"""
import requests
import json
import sys

API_BASE = "https://scare-unified-dash-production.up.railway.app"

def print_separator():
    print("-" * 80)

def check_endpoint(url):
    print(f"Checking endpoint: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        data = response.json()
        print(f"Response status: {response.status_code}")
        print(f"Response size: {len(data)} items")
        
        if isinstance(data, list) and len(data) > 0:
            # Show sample of first item
            print("\nSample data (first item):")
            print(json.dumps(data[0], indent=2))
        elif isinstance(data, dict):
            # Show entire response for dict objects
            print("\nResponse data:")
            print(json.dumps(data, indent=2))
        else:
            print("\nEmpty response or non-standard format")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def main():
    print_separator()
    print("CHECKING API ENDPOINTS")
    print_separator()
    
    # Check health endpoint
    health_data = check_endpoint(f"{API_BASE}/health")
    print_separator()
    
    # Check campaign mappings
    print("Checking mapped campaigns:")
    mappings = check_endpoint(f"{API_BASE}/api/campaign-mappings")
    print_separator()
    
    # Check unmapped campaigns
    print("Checking unmapped campaigns:")
    unmapped = check_endpoint(f"{API_BASE}/api/unmapped-campaigns")
    print_separator()
    
    # Check hierarchical view
    print("Checking hierarchical campaigns:")
    hierarchical = check_endpoint(f"{API_BASE}/api/campaigns-hierarchical")
    print_separator()
    
    # Summary
    print("API CHECK SUMMARY")
    print_separator()
    print(f"Health endpoint: {'OK' if health_data else 'FAILED'}")
    print(f"Mapped campaigns: {len(mappings) if mappings else 'FAILED'}")
    print(f"Unmapped campaigns: {len(unmapped) if unmapped else 'FAILED'}")
    print(f"Hierarchical campaigns: {len(hierarchical) if hierarchical else 'FAILED'}")
    print_separator()

if __name__ == "__main__":
    main()
