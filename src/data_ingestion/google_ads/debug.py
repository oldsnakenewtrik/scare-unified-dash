import os
from dotenv import load_dotenv
import sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('google_ads_debug')

# Load environment variables
load_dotenv()

# Print credentials
logger.info(f"Developer Token: {os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN')}")
logger.info(f"Customer ID: {os.getenv('GOOGLE_ADS_CUSTOMER_ID')}")
logger.info(f"Client ID: {os.getenv('GOOGLE_ADS_CLIENT_ID')[:15]}...")
logger.info(f"Client Secret: {os.getenv('GOOGLE_ADS_CLIENT_SECRET')[:10]}...")
logger.info(f"Refresh Token: {os.getenv('GOOGLE_ADS_REFRESH_TOKEN')[:15]}...")

# Try to create client from environment
try:
    logger.info("Attempting to create client from environment variables...")
    client = GoogleAdsClient.load_from_env(version="v14")
    logger.info("✅ Successfully created client from environment")
except Exception as e:
    logger.error(f"❌ Failed to create client from environment: {str(e)}")

# Try to create client from dictionary
try:
    logger.info("Attempting to create client from dictionary...")
    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": True,
        "version": "v14"
    }
    client = GoogleAdsClient.load_from_dict(credentials)
    logger.info("✅ Successfully created client from dictionary")
    
    # Test API query
    try:
        ga_service = client.get_service("GoogleAdsService")
        customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
        
        logger.info(f"Testing API query for customer ID: {customer_id}")
        
        query = """
            SELECT customer.id, customer.descriptive_name
            FROM customer
            LIMIT 1
        """
        
        response = ga_service.search_stream(customer_id=customer_id, query=query)
        
        # Process the response
        for batch in response:
            for row in batch.results:
                logger.info(f"✅ Successfully connected to Google Ads account: {row.customer.descriptive_name} (ID: {row.customer.id})")
                sys.exit(0)
        
        logger.info("✅ Connected to API but no account information found.")
        
    except GoogleAdsException as ex:
        logger.error(f"❌ Google Ads API error: {ex.error.code().name}")
        for error in ex.failure.errors:
            logger.error(f"  - Error message: {error.message}")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    logger.error(f"    - On field: {field_path_element.field_name}")
            
except Exception as e:
    logger.error(f"❌ Failed to create client from dictionary: {str(e)}")
