import os
import logging
import yaml
import sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('google_ads_yaml_test')

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the YAML file
yaml_path = os.path.join(script_dir, 'google-ads.yaml')
logger.info(f"Looking for YAML file at: {yaml_path}")

if not os.path.exists(yaml_path):
    logger.error(f"YAML file not found at {yaml_path}")
    sys.exit(1)

try:
    # Log that we're loading from YAML
    logger.info(f"Loading client configuration from YAML file")
    
    # Initialize the client from YAML
    client = GoogleAdsClient.load_from_storage(yaml_path)
    logger.info("Client created successfully from YAML!")
    
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
    
    # Get the customer ID from YAML
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)
    
    customer_id = config.get('linked_customer_id') or config.get('login_customer_id')
    logger.info(f"Using customer ID from YAML: {customer_id}")
    
    # Execute the query
    logger.info(f"Executing query: {query}")
    response = service.search(customer_id=customer_id, query=query)
    
    # Process the results
    result_count = 0
    for row in response:
        result_count += 1
        logger.info(f"Campaign ID: {row.campaign.id}, Name: {row.campaign.name}")
    
    logger.info(f"Search completed successfully! Found {result_count} campaigns.")
except GoogleAdsException as ex:
    logger.error(f"Request with ID '{ex.request_id}' failed with status "
                f"'{ex.error.code().name}' and includes the following errors:")
    for error in ex.failure.errors:
        logger.error(f"\tError with message '{error.message}'.")
        if error.location:
            for field_path_element in error.location.field_path_elements:
                logger.error(f"\t\tOn field: {field_path_element.field_name}")
except Exception as e:
    logger.error(f"An unexpected error occurred: {str(e)}")
