#!/usr/bin/env python

"""
This script will clear all mappings for Google Ads campaigns to force them to show as unmapped.
"""

import os
import sys
import logging
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("unmapping_script")

# Load environment variables
load_dotenv()

# Check API endpoint first
def check_api():
    """Check if API is accessible"""
    try:
        # Check health endpoint first
        health_url = "https://scare-unified-dash-production.up.railway.app/health"
        logger.info(f"Checking API health at {health_url}")
        
        health_response = requests.get(health_url)
        if health_response.status_code == 200:
            health_data = health_response.json()
            logger.info(f"API health check successful: {health_data.get('status', 'unknown')}")
            logger.info(f"Database status: {health_data.get('database_status', 'unknown')}")
            
            # Log table counts
            row_counts = health_data.get('row_counts', {})
            logger.info(f"Row counts: {row_counts}")
            
            # Log unmapped campaigns
            unmapped = health_data.get('unmapped_campaigns', 'unknown')
            logger.info(f"Unmapped campaigns: {unmapped}")
            
            # Check campaign examples
            campaign_examples = health_data.get('campaign_examples', {})
            for source, campaigns in campaign_examples.items():
                logger.info(f"Example {source} campaigns: {campaigns}")
        else:
            logger.error(f"Health check failed with status code {health_response.status_code}")
            return False
        
        # Now check unmapped campaigns
        unmapped_url = "https://scare-unified-dash-production.up.railway.app/api/unmapped-campaigns"
        logger.info(f"Checking unmapped campaigns at {unmapped_url}")
        
        unmapped_response = requests.get(unmapped_url)
        if unmapped_response.status_code == 200:
            unmapped_data = unmapped_response.json()
            logger.info(f"Found {len(unmapped_data)} unmapped campaigns")
            
            if len(unmapped_data) > 0:
                logger.info("Examples of unmapped campaigns:")
                for i, campaign in enumerate(unmapped_data[:5]):
                    logger.info(f"{i+1}. {campaign.get('source_system')}: {campaign.get('campaign_name')} (ID: {campaign.get('external_campaign_id')})")
            else:
                logger.warning("No unmapped campaigns found")
        else:
            logger.error(f"Unmapped campaigns check failed with status code {unmapped_response.status_code}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking API: {str(e)}")
        return False

# Function to clear Google Ads campaign mappings
def clear_google_ads_mappings():
    """Clear all Google Ads campaign mappings"""
    try:
        # Get database URL
        DATABASE_URL = os.getenv("RAILWAY_DATABASE_URL", os.getenv("DATABASE_URL"))
        if not DATABASE_URL:
            logger.error("DATABASE_URL environment variable not set")
            return False
        
        # Connect to database
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # First check existing mappings
            check_query = """
            SELECT COUNT(*) FROM sm_campaign_name_mapping
            WHERE source_system = 'Google Ads'
            """
            count = conn.execute(text(check_query)).scalar() or 0
            logger.info(f"Found {count} existing Google Ads mappings")
            
            if count == 0:
                logger.info("No Google Ads mappings to clear")
                return True
            
            # Delete all Google Ads mappings
            delete_query = """
            DELETE FROM sm_campaign_name_mapping
            WHERE source_system = 'Google Ads'
            """
            result = conn.execute(text(delete_query))
            conn.commit()
            
            logger.info(f"Cleared {result.rowcount} Google Ads mappings")
            
            # Verify
            verify_query = """
            SELECT COUNT(*) FROM sm_campaign_name_mapping
            WHERE source_system = 'Google Ads'
            """
            verify_count = conn.execute(text(verify_query)).scalar() or 0
            logger.info(f"Remaining Google Ads mappings: {verify_count}")
            
            return verify_count == 0
    except Exception as e:
        logger.error(f"Error clearing Google Ads mappings: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting unmapping process")
    
    # First check API
    logger.info("Checking API endpoints")
    api_check = check_api()
    
    if api_check:
        # If API is accessible, clear Google Ads mappings
        logger.info("API check successful, proceeding to clear Google Ads mappings")
        success = clear_google_ads_mappings()
        
        if success:
            logger.info("Successfully cleared Google Ads mappings")
            
            # Check API again to verify
            logger.info("Checking API again to verify unmapped campaigns")
            check_api()
        else:
            logger.error("Failed to clear Google Ads mappings")
    else:
        logger.error("API check failed, aborting")
    
    logger.info("Unmapping process completed")
