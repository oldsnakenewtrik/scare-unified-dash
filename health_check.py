#!/usr/bin/env python
"""
Health check script for SCARE Unified Dashboard
This script checks the health of the application and triggers data ingestion if needed.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('health_check')

def check_api_health(base_url):
    """
    Check the health of the API service
    """
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code != 200:
            logger.error(f"API health check failed with status code {response.status_code}")
            return False, response.text
        
        health_data = response.json()
        logger.info(f"API health status: {health_data.get('status', 'unknown')}")
        
        # Check if there are any unhealthy components
        components = health_data.get('components', {})
        for component_name, component_data in components.items():
            if component_data.get('status') == 'unhealthy':
                logger.error(f"Component {component_name} is unhealthy: {component_data.get('error')}")
                return False, health_data
        
        # Check if there are any warnings
        has_warnings = False
        for component_name, component_data in components.items():
            if component_data.get('status') == 'warning':
                logger.warning(f"Component {component_name} has a warning: {component_data.get('error')}")
                has_warnings = True
        
        return True, health_data
    
    except Exception as e:
        logger.error(f"Error checking API health: {str(e)}")
        return False, str(e)

def check_database_data(health_data):
    """
    Check if there is data in the database
    """
    try:
        # Check data component
        data_component = health_data.get('components', {}).get('data', {})
        table_counts = data_component.get('counts', {})
        
        # Check if we have any data in the fact tables
        total_records = sum(count for count in table_counts.values())
        if total_records == 0:
            logger.warning("No data found in any fact tables")
            return False
        
        # Log data counts
        for table, count in table_counts.items():
            logger.info(f"Table {table}: {count} records")
        
        return True
    
    except Exception as e:
        logger.error(f"Error checking database data: {str(e)}")
        return False

def check_campaign_mappings(health_data):
    """
    Check if there are campaign mappings
    """
    try:
        # Check mappings component
        mappings_component = health_data.get('components', {}).get('mappings', {})
        mappings_status = mappings_component.get('status')
        
        if mappings_status == 'unhealthy':
            logger.error(f"Campaign mappings are unhealthy: {mappings_component.get('error')}")
            return False
        
        if mappings_status == 'warning':
            logger.warning(f"Campaign mappings have a warning: {mappings_component.get('error')}")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error checking campaign mappings: {str(e)}")
        return False

def check_unmapped_campaigns(base_url):
    """
    Check if there are unmapped campaigns
    """
    try:
        response = requests.get(f"{base_url}/api/unmapped-campaigns", timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to check unmapped campaigns: {response.status_code}")
            return False, []
        
        unmapped_campaigns = response.json()
        logger.info(f"Found {len(unmapped_campaigns)} unmapped campaigns")
        
        # Log first few unmapped campaigns
        for i, campaign in enumerate(unmapped_campaigns[:5]):
            logger.info(f"Unmapped campaign {i+1}: {campaign}")
        
        return True, unmapped_campaigns
    
    except Exception as e:
        logger.error(f"Error checking unmapped campaigns: {str(e)}")
        return False, []

def trigger_google_ads_etl():
    """
    Trigger Google Ads ETL process
    """
    try:
        logger.info("Triggering Google Ads ETL process...")
        
        # Run the ETL process
        result = subprocess.run(
            ["python", "-m", "src.data_ingestion.google_ads.main", "--run-once"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Google Ads ETL process failed: {result.stderr}")
            return False
        
        logger.info("Google Ads ETL process completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error triggering Google Ads ETL process: {str(e)}")
        return False

def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description='Health check script for SCARE Unified Dashboard')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL for the API service')
    parser.add_argument('--trigger-etl', action='store_true', help='Trigger ETL process if no data is found')
    args = parser.parse_args()
    
    logger.info("Starting health check...")
    
    # Check API health
    api_healthy, health_data = check_api_health(args.base_url)
    if not api_healthy:
        logger.error("API health check failed")
        sys.exit(1)
    
    # Check database data
    if isinstance(health_data, dict):
        has_data = check_database_data(health_data)
        if not has_data and args.trigger_etl:
            logger.info("No data found, triggering ETL process...")
            trigger_google_ads_etl()
    
    # Check campaign mappings
    if isinstance(health_data, dict):
        has_mappings = check_campaign_mappings(health_data)
        if not has_mappings:
            logger.warning("Campaign mappings check failed")
    
    # Check unmapped campaigns
    unmapped_check_success, unmapped_campaigns = check_unmapped_campaigns(args.base_url)
    if unmapped_check_success and len(unmapped_campaigns) > 0:
        logger.warning(f"Found {len(unmapped_campaigns)} unmapped campaigns")
    
    logger.info("Health check completed")

if __name__ == "__main__":
    main()
