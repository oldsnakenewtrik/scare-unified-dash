#!/usr/bin/env python3
"""
Script to directly check the Google Ads API connection.
This script will attempt to connect to the Google Ads API and fetch a small amount of data
to verify that the credentials and API access are working correctly.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import traceback
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('google_ads_api_check')

# Check if environment variables are set
required_vars = [
    'GOOGLE_ADS_DEVELOPER_TOKEN',
    'GOOGLE_ADS_CLIENT_ID',
    'GOOGLE_ADS_CLIENT_SECRET',
    'GOOGLE_ADS_REFRESH_TOKEN',
    'GOOGLE_ADS_CUSTOMER_ID'
]

missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

GOOGLE_ADS_CUSTOMER_ID = os.environ.get('GOOGLE_ADS_CUSTOMER_ID')

def get_google_ads_client():
    """Initialize and return a Google Ads API client."""
    try:
        logger.info("Initializing Google Ads client")
        client = GoogleAdsClient.load_from_env()
        logger.info("Google Ads client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Error initializing Google Ads client: {str(e)}")
        traceback.print_exc()
        return None

def check_api_connection():
    """Test the connection to the Google Ads API."""
    client = get_google_ads_client()
    if not client:
        logger.error("Failed to create Google Ads client")
        return False
    
    try:
        logger.info("Testing Google Ads API connection")
        
        # Get the Google Ads service
        ga_service = client.get_service("GoogleAdsService")
        
        # Calculate date range for the last 7 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        # Simple query to get basic account information
        query = f"""
            SELECT
              customer.id,
              customer.descriptive_name
            FROM customer
            LIMIT 1
        """
        
        logger.info(f"Executing simple test query")
        
        # Create a search request
        search_request = client.get_type("SearchGoogleAdsRequest")
        search_request.customer_id = GOOGLE_ADS_CUSTOMER_ID
        search_request.query = query
        
        # Execute the request
        response = ga_service.search(request=search_request)
        
        # Log the response
        for row in response.results:
            logger.info(f"Account found: {row.customer.descriptive_name} (ID: {row.customer.id})")
        
        # Now try a query with more fields to test the actual campaign data access
        campaign_query = f"""
            SELECT
              campaign.id,
              campaign.name,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            LIMIT 5
        """
        
        logger.info(f"Executing campaign test query")
        
        # Update the search request with the new query
        search_request.query = campaign_query
        
        # Execute the request
        campaign_response = ga_service.search(request=search_request)
        
        # Log the response
        campaign_count = 0
        for row in campaign_response.results:
            campaign_count += 1
            logger.info(f"Campaign found: {row.campaign.name} (ID: {row.campaign.id})")
            logger.info(f"  Metrics - Impressions: {row.metrics.impressions}, Clicks: {row.metrics.clicks}")
        
        logger.info(f"Found {campaign_count} campaigns in the test query")
        
        return True
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API Error: {ex}")
        logger.error(f"Request ID: {ex.request_id}")
        for error in ex.failure.errors:
            logger.error(f"\tError with message: {error.message}")
            logger.error(f"\tError code: {error.error_code}")
            logger.error(f"\tError location: {error.location}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when checking Google Ads API connection: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting Google Ads API check")
    success = check_api_connection()
    if success:
        logger.info("Google Ads API connection check completed successfully")
        sys.exit(0)
    else:
        logger.error("Google Ads API connection check failed")
        sys.exit(1)
