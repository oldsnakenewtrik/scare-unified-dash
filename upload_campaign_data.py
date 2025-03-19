"""
Script to upload real Google Ads campaign data to the production Railway database.
"""
import os
import sys
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("upload_campaigns")

# Production API base URL
API_URL = "https://scare-unified-dash-production.up.railway.app"

def check_api_health():
    """Check if the API is healthy and return database status"""
    try:
        response = requests.get(f"{API_URL}/health")
        response.raise_for_status()
        health_data = response.json()
        logger.info(f"API Status: {health_data.get('status')}")
        logger.info(f"Database Status: {health_data.get('database_status')}")
        
        # Check for data in tables
        if 'row_counts' in health_data:
            for table, count in health_data['row_counts'].items():
                logger.info(f"Table {table}: {count} rows")
        
        # Check for campaign examples
        if 'campaign_examples' in health_data:
            for source, examples in health_data['campaign_examples'].items():
                if isinstance(examples, list) and examples:
                    logger.info(f"{source} campaign examples:")
                    for ex in examples:
                        logger.info(f"  - {ex.get('name')} (ID: {ex.get('id')})")
        
        return health_data
    except Exception as e:
        logger.error(f"Failed to check API health: {str(e)}")
        return None

def upload_google_ads_data():
    """Upload Google Ads data from local JSON file to production database"""
    data_file = 'data/google_ads_data_2025-03-12_to_2025-03-19_20250319_132330.json'
    
    try:
        # Read the JSON file
        with open(data_file, 'r') as file:
            campaigns_data = json.load(file)
        
        logger.info(f"Loaded {len(campaigns_data)} records from {data_file}")
        
        # Prepare data for batch upload
        # Group by campaign ID to get unique campaigns
        unique_campaigns = {}
        for item in campaigns_data:
            campaign_id = str(item['campaign_id'])
            if campaign_id not in unique_campaigns:
                unique_campaigns[campaign_id] = {
                    'campaign_id': campaign_id,
                    'campaign_name': item['campaign_name'],
                    'source_system': 'Google Ads'
                }
        
        # Create campaign mappings for each unique campaign
        for campaign_id, campaign in unique_campaigns.items():
            # Derive a pretty name from the original name
            original_name = campaign['campaign_name']
            pretty_name = original_name
            # Basic categorization based on name keywords
            category = "Uncategorized"
            campaign_type = "Uncategorized"
            network = "Search"  # Default for Google Ads
            
            # Simple logic to categorize based on campaign name
            if "brand" in original_name.lower():
                campaign_type = "Brand"
            elif "search" in original_name.lower():
                campaign_type = "Search"
                category = "Search"
            elif "display" in original_name.lower():
                campaign_type = "Display"
                category = "Display"
                network = "Display"
            elif "shopping" in original_name.lower() or "pmax" in original_name.lower():
                campaign_type = "Shopping"
                category = "Shopping"
                network = "Shopping"
            
            # Prepare mapping data
            mapping_data = {
                'source_system': 'Google Ads',
                'external_campaign_id': campaign_id,
                'original_campaign_name': original_name,
                'pretty_campaign_name': pretty_name,
                'campaign_category': category,
                'campaign_type': campaign_type,
                'network': network
            }
            
            logger.info(f"Creating mapping for: {original_name} (ID: {campaign_id})")
            
            try:
                # Send POST request to create mapping
                response = requests.post(
                    f"{API_URL}/api/campaign-mappings",
                    json=mapping_data
                )
                
                if response.status_code == 200:
                    logger.info(f"✓ Successfully mapped campaign: {original_name}")
                else:
                    logger.warning(f"✗ Failed to map campaign: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Error creating mapping: {str(e)}")
        
        logger.info(f"Processed {len(unique_campaigns)} unique campaigns")
        return True
    
    except Exception as e:
        logger.error(f"Error uploading Google Ads data: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting campaign data upload process")
    
    # First check API health
    health_data = check_api_health()
    
    if health_data and health_data.get('status') == 'healthy':
        # If API is healthy, proceed with upload
        logger.info("API is healthy, proceeding with data upload")
        upload_google_ads_data()
    else:
        logger.error("API health check failed, aborting upload")
    
    logger.info("Upload process completed")
