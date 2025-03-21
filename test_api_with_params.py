#!/usr/bin/env python
import requests
import logging
import json
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API endpoints to test
API_BASE_URL = "https://scare-unified-dash-production.up.railway.app"

def test_campaign_metrics_endpoint():
    """Test the campaign metrics endpoint with proper date parameters"""
    # Set up date parameters - one year of data
    end_date = datetime.date.today()
    start_date = end_date.replace(year=end_date.year - 1)
    
    # Format dates as strings
    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()
    
    # Build URL with query parameters
    url = f"{API_BASE_URL}/api/campaign-metrics?start_date={start_date_str}&end_date={end_date_str}&platform=google_ads"
    
    logger.info(f"Testing endpoint: {url}")
    
    try:
        # Make the request
        response = requests.get(url)
        
        # Log status
        logger.info(f"Status code: {response.status_code}")
        
        # Check if successful
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Received {len(data)} items")
            
            if len(data) > 0:
                # Display the first item as a sample
                logger.info(f"Sample item: {json.dumps(data[0], indent=2)}")
            else:
                logger.info("No data returned")
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
    
    except Exception as e:
        logger.error(f"Error testing endpoint: {e}")

if __name__ == "__main__":
    test_campaign_metrics_endpoint()
