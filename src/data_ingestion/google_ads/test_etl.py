"""
Test script for Google Ads ETL process
"""
import os
import logging
import sys
from datetime import datetime, timedelta
from main import (
    get_google_ads_client,
    fetch_google_ads_data,
    process_google_ads_data,
    check_google_ads_health
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_ads_etl_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("google_ads_etl_test")

def test_etl_process():
    """Test the ETL process for Google Ads data"""
    logger.info("Starting Google Ads ETL test")
    
    try:
        # First test the client creation
        client = get_google_ads_client()
        if client:
            logger.info("Google Ads client created successfully")
        else:
            logger.error("Failed to create Google Ads client")
            return False
        
        # Test health check
        if check_google_ads_health():
            logger.info("Google Ads health check passed")
        else:
            logger.error("Google Ads health check failed")
            return False
        
        # Test data fetching (last 7 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Fetching data from {start_date_str} to {end_date_str}")
        raw_data = fetch_google_ads_data(start_date_str, end_date_str)
        
        if not raw_data:
            logger.error("Failed to fetch any data from Google Ads API")
            return False
        
        logger.info(f"Successfully fetched {len(raw_data)} rows of data")
        
        # Test data processing
        processed_data = process_google_ads_data(raw_data)
        logger.info(f"Successfully processed {len(processed_data)} rows of data")
        
        # Print a sample record for inspection
        if processed_data:
            sample = processed_data[0]
            logger.info("Sample processed record:")
            for key, value in sample.items():
                logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing Google Ads ETL: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_etl_process()
    if success:
        logger.info("ETL test completed successfully")
        print("✓ Google Ads ETL test passed")
    else:
        logger.error("ETL test failed")
        print("✗ Google Ads ETL test failed")
