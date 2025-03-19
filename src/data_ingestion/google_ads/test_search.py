import os
import logging
import dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# Load environment variables from .env file
dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('google_ads_test')

try:
    # Create client config from environment variables
    client_config = {
        'developer_token': os.environ.get('GOOGLE_ADS_DEVELOPER_TOKEN'),
        'client_id': os.environ.get('GOOGLE_ADS_CLIENT_ID'),
        'client_secret': os.environ.get('GOOGLE_ADS_CLIENT_SECRET'),
        'refresh_token': os.environ.get('GOOGLE_ADS_REFRESH_TOKEN'),
        'use_proto_plus': True
    }
    
    # Check if any required values are missing
    missing_values = [k for k, v in client_config.items() if v is None]
    if missing_values:
        logger.error(f"Missing required values: {missing_values}")
        exit(1)
    
    # Log config values (without secrets)
    logger.info(f"Developer Token: {client_config['developer_token'][:5]}...")
    logger.info(f"Client ID: {client_config['client_id'][:15]}...")
    
    # Initialize the client
    client = GoogleAdsClient.load_from_dict(client_config)
    logger.info("Client created successfully!")
    
    # Get the service
    service = client.get_service('GoogleAdsService')
    
    # Create a simple query
    query = """
        SELECT 
            campaign.id, 
            campaign.name 
        FROM campaign 
        LIMIT 10
    """
    
    # Get the customer ID
    customer_id = os.environ.get('GOOGLE_ADS_CUSTOMER_ID')
    if not customer_id:
        logger.error("Missing GOOGLE_ADS_CUSTOMER_ID environment variable")
        exit(1)
    
    logger.info(f"Using customer ID: {customer_id}")
    
    # Execute the query
    response = service.search(customer_id=customer_id, query=query)
    
    # Process the results
    for row in response:
        logger.info(f"Campaign ID: {row.campaign.id}, Name: {row.campaign.name}")
    
    logger.info("Search completed successfully!")
except GoogleAdsException as ex:
    logger.error(f"Request with ID '{ex.request_id}' failed with status "
                f"'{ex.error.code().name}' and includes the following errors:")
    for error in ex.failure.errors:
        logger.error(f"\tError with message '{error.message}'.")
        if error.location:
            for field_path_element in error.location.field_path_elements:
                logger.error(f"\t\tOn field: {field_path_element.field_name}")
except Exception as e:
    logger.error(f"An unexpected error occurred: {e}")
