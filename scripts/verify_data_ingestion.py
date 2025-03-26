#!/usr/bin/env python
"""
Verify Data Ingestion and Campaign Mapping

This script verifies that data ingestion is working properly and that campaign mappings
are being correctly detected. It can also trigger data ingestion if needed.
"""

import os
import sys
import logging
import argparse
import requests
import json
import time
from datetime import datetime, timedelta
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("verify_data_ingestion")

def check_api_health(api_url="http://localhost:8000"):
    """Check the health of the API"""
    try:
        logger.info(f"Checking API health at {api_url}/health")
        response = requests.get(f"{api_url}/health", timeout=10)
        response.raise_for_status()
        health_data = response.json()
        
        logger.info(f"API health status: {health_data.get('status', 'unknown')}")
        
        # Print component statuses
        components = health_data.get('components', {})
        for component_name, component_data in components.items():
            status = component_data.get('status', 'unknown')
            logger.info(f"- {component_name}: {status}")
            if status != 'healthy' and component_data.get('error'):
                logger.warning(f"  Error: {component_data.get('error')}")
        
        return health_data.get('status') == 'healthy'
    except Exception as e:
        logger.error(f"Error checking API health: {str(e)}")
        return False

def check_unmapped_campaigns(api_url="http://localhost:8000"):
    """Check for unmapped campaigns"""
    try:
        logger.info(f"Checking for unmapped campaigns at {api_url}/api/unmapped-campaigns")
        response = requests.get(f"{api_url}/api/unmapped-campaigns", timeout=10)
        response.raise_for_status()
        campaigns = response.json()
        
        logger.info(f"Found {len(campaigns)} unmapped campaigns")
        
        # Group by source system
        by_source = {}
        for campaign in campaigns:
            source = campaign.get('source_system', 'unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(campaign)
        
        # Print summary by source
        for source, campaigns in by_source.items():
            logger.info(f"- {source}: {len(campaigns)} campaigns")
            # Print a few examples
            for i, campaign in enumerate(campaigns[:3]):
                logger.info(f"  - {campaign.get('campaign_name')} (ID: {campaign.get('external_campaign_id')})")
                if i >= 2 and len(campaigns) > 3:
                    logger.info(f"  - ... and {len(campaigns) - 3} more")
                    break
        
        return campaigns
    except Exception as e:
        logger.error(f"Error checking unmapped campaigns: {str(e)}")
        return []

def check_existing_mappings(api_url="http://localhost:8000"):
    """Check existing campaign mappings"""
    try:
        logger.info(f"Checking existing campaign mappings at {api_url}/api/campaign-mappings")
        response = requests.get(f"{api_url}/api/campaign-mappings", timeout=10)
        response.raise_for_status()
        mappings = response.json()
        
        logger.info(f"Found {len(mappings)} existing campaign mappings")
        
        # Group by source system
        by_source = {}
        for mapping in mappings:
            source = mapping.get('source_system', 'unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(mapping)
        
        # Print summary by source
        for source, mappings in by_source.items():
            logger.info(f"- {source}: {len(mappings)} mappings")
            # Print a few examples
            for i, mapping in enumerate(mappings[:3]):
                logger.info(f"  - {mapping.get('original_campaign_name')} -> {mapping.get('pretty_campaign_name')}")
                if i >= 2 and len(mappings) > 3:
                    logger.info(f"  - ... and {len(mappings) - 3} more")
                    break
        
        return mappings
    except Exception as e:
        logger.error(f"Error checking existing mappings: {str(e)}")
        return []

def create_sample_mapping(campaign, api_url="http://localhost:8000"):
    """Create a sample mapping for a campaign"""
    try:
        source_system = campaign.get('source_system')
        external_campaign_id = campaign.get('external_campaign_id')
        original_name = campaign.get('campaign_name')
        
        # Generate a pretty name based on the original
        pretty_name = f"Pretty: {original_name}"
        
        # Determine category, type, and network based on the name
        category = "Non-Brand"
        if "brand" in original_name.lower():
            category = "Brand"
        
        campaign_type = "Search"
        if "display" in original_name.lower():
            campaign_type = "Display"
        elif "shopping" in original_name.lower():
            campaign_type = "Shopping"
        
        network = "Search Network"
        if "display" in original_name.lower():
            network = "Display Network"
        elif "shopping" in original_name.lower():
            network = "Shopping Network"
        
        # Create the mapping
        mapping_data = {
            "source_system": source_system,
            "external_campaign_id": external_campaign_id,
            "original_campaign_name": original_name,
            "pretty_campaign_name": pretty_name,
            "campaign_category": category,
            "campaign_type": campaign_type,
            "network": network,
            "display_order": 0
        }
        
        logger.info(f"Creating sample mapping for {original_name}")
        response = requests.post(
            f"{api_url}/api/campaign-mappings",
            json=mapping_data,
            timeout=10
        )
        response.raise_for_status()
        new_mapping = response.json()
        
        logger.info(f"Created mapping: {original_name} -> {pretty_name}")
        return new_mapping
    except Exception as e:
        logger.error(f"Error creating sample mapping: {str(e)}")
        return None

def trigger_google_ads_etl():
    """Trigger Google Ads ETL process"""
    try:
        logger.info("Triggering Google Ads ETL process")
        
        # Check if we're in a Docker container
        if os.path.exists('/.dockerenv'):
            # We're in a container, use the container path
            cmd = ["python", "/app/src/data_ingestion/google_ads/main.py", "--run-once"]
        else:
            # We're on the host, use the relative path
            cmd = ["python", "src/data_ingestion/google_ads/main.py", "--run-once"]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ETL process failed with code {process.returncode}")
            logger.error(f"Error: {stderr.decode('utf-8')}")
            return False
        
        logger.info("ETL process completed successfully")
        logger.info(f"Output: {stdout.decode('utf-8')}")
        return True
    except Exception as e:
        logger.error(f"Error triggering ETL process: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Verify Data Ingestion and Campaign Mapping')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API URL')
    parser.add_argument('--trigger-etl', action='store_true', help='Trigger Google Ads ETL process')
    parser.add_argument('--create-mappings', action='store_true', help='Create sample mappings for unmapped campaigns')
    parser.add_argument('--max-mappings', type=int, default=5, help='Maximum number of sample mappings to create')
    
    args = parser.parse_args()
    
    # Check API health
    if not check_api_health(args.api_url):
        logger.error("API is not healthy, exiting")
        return 1
    
    # Trigger ETL if requested
    if args.trigger_etl:
        if not trigger_google_ads_etl():
            logger.error("Failed to trigger ETL process")
            return 1
        
        # Wait for ETL to complete
        logger.info("Waiting for ETL process to complete...")
        time.sleep(10)
    
    # Check for unmapped campaigns
    unmapped_campaigns = check_unmapped_campaigns(args.api_url)
    
    # Check existing mappings
    existing_mappings = check_existing_mappings(args.api_url)
    
    # Create sample mappings if requested
    if args.create_mappings and unmapped_campaigns:
        logger.info(f"Creating up to {args.max_mappings} sample mappings")
        
        for i, campaign in enumerate(unmapped_campaigns[:args.max_mappings]):
            create_sample_mapping(campaign, args.api_url)
            # Small delay to avoid overwhelming the API
            time.sleep(0.5)
        
        # Check mappings again
        logger.info("Checking mappings after creating samples")
        check_existing_mappings(args.api_url)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
