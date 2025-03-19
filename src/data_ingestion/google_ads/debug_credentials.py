#!/usr/bin/env python

"""
Debug script to diagnose Google Ads API credential issues on Railway.
This script will:
1. Check all environment variables
2. Verify Google Ads API credential presence
3. Test connecting to the Google Ads API
4. Log detailed information about any failures
"""

import os
import sys
import logging
import json
import datetime
from pathlib import Path
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("debug_credentials")

def check_environment_variables():
    """Check all environment variables, especially Google Ads credentials"""
    logger.info("Checking environment variables...")
    
    # List of critical Google Ads variables
    critical_vars = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID"
    ]
    
    # Check each critical variable
    missing_vars = []
    for var in critical_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if "SECRET" in var or "TOKEN" in var:
                masked_value = value[:4] + "****" + value[-4:]
                logger.info(f"✅ {var} is set: {masked_value}")
            else:
                logger.info(f"✅ {var} is set: {value}")
        else:
            logger.error(f"❌ {var} is NOT set")
            missing_vars.append(var)
    
    # Log all environment variables (with sensitive data masked)
    logger.info("All environment variables:")
    for key, value in os.environ.items():
        if "SECRET" in key or "TOKEN" in key or "PASSWORD" in key or "KEY" in key:
            masked_value = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
            logger.info(f"  {key}={masked_value}")
        else:
            logger.info(f"  {key}={value}")
    
    return missing_vars

def check_google_ads_yaml():
    """Check if google-ads.yaml file exists and is configured correctly"""
    logger.info("Checking google-ads.yaml configuration...")
    
    # Possible locations for google-ads.yaml
    possible_locations = [
        "./google-ads.yaml",
        "/app/google-ads.yaml",
        "src/data_ingestion/google_ads/google-ads.yaml",
        "/app/src/data_ingestion/google_ads/google-ads.yaml",
        str(Path.home() / "google-ads.yaml")
    ]
    
    yaml_file = None
    for location in possible_locations:
        if os.path.exists(location):
            yaml_file = location
            logger.info(f"Found google-ads.yaml at {location}")
            break
    
    if not yaml_file:
        logger.error("❌ google-ads.yaml not found in any expected location")
        
        # Create a new google-ads.yaml file using environment variables
        logger.info("Creating google-ads.yaml from environment variables...")
        
        config = {
            "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID", ""),
            "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET", ""),
            "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
            "login_customer_id": os.environ.get("GOOGLE_ADS_CUSTOMER_ID", ""),
            "use_proto_plus": True
        }
        
        # Create yaml file
        with open("google-ads.yaml", "w") as f:
            yaml.dump(config, f)
        
        logger.info("Created google-ads.yaml with environment variables")
        yaml_file = "google-ads.yaml"
    
    # Read and validate the yaml file
    try:
        with open(yaml_file, "r") as f:
            config = yaml.safe_load(f)
        
        # Check required fields
        required_fields = ["developer_token", "client_id", "client_secret", "refresh_token"]
        missing_fields = []
        
        for field in required_fields:
            if field not in config or not config[field]:
                missing_fields.append(field)
                logger.error(f"❌ {field} is missing or empty in google-ads.yaml")
            else:
                # Mask sensitive values
                if field in ["developer_token", "client_secret", "refresh_token"]:
                    masked_value = config[field][:4] + "****" + config[field][-4:] if len(config[field]) > 8 else "****"
                    logger.info(f"✅ {field} is set in google-ads.yaml: {masked_value}")
                else:
                    logger.info(f"✅ {field} is set in google-ads.yaml: {config[field]}")
        
        if missing_fields:
            logger.error(f"google-ads.yaml is missing required fields: {missing_fields}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error reading google-ads.yaml: {str(e)}")
        return False

def test_google_ads_connection():
    """Test connection to Google Ads API"""
    logger.info("Testing connection to Google Ads API...")
    
    try:
        # Attempt to import the Google Ads client library
        try:
            from google.ads.googleads.client import GoogleAdsClient
            logger.info("✅ Successfully imported GoogleAdsClient")
        except ImportError as e:
            logger.error(f"❌ Failed to import GoogleAdsClient: {str(e)}")
            logger.info("Trying to install the Google Ads client library...")
            os.system("pip install google-ads")
            
            try:
                from google.ads.googleads.client import GoogleAdsClient
                logger.info("✅ Successfully imported GoogleAdsClient after installation")
            except ImportError as e:
                logger.error(f"❌ Still failed to import GoogleAdsClient: {str(e)}")
                return False
        
        # Load credentials from google-ads.yaml
        try:
            client = GoogleAdsClient.load_from_storage("google-ads.yaml")
            logger.info("✅ Successfully loaded credentials from google-ads.yaml")
        except Exception as e:
            logger.error(f"❌ Failed to load credentials from google-ads.yaml: {str(e)}")
            
            # Try loading from environment variables directly
            try:
                client = GoogleAdsClient.load_from_dict({
                    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
                    "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID", ""),
                    "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET", ""),
                    "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
                    "login_customer_id": os.environ.get("GOOGLE_ADS_CUSTOMER_ID", ""),
                    "use_proto_plus": True
                })
                logger.info("✅ Successfully loaded credentials from environment variables")
            except Exception as e:
                logger.error(f"❌ Failed to load credentials from environment variables: {str(e)}")
                return False
        
        # Try to make a simple API call
        try:
            customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")
            if not customer_id:
                logger.error("❌ GOOGLE_ADS_CUSTOMER_ID is not set")
                return False
            
            logger.info(f"Making test API call for customer ID: {customer_id}")
            ga_service = client.get_service("GoogleAdsService")
            query = """
                SELECT 
                    campaign.id, 
                    campaign.name
                FROM campaign
                ORDER BY campaign.name
                LIMIT 10
            """
            
            search_request = client.get_type("SearchGoogleAdsRequest")
            search_request.customer_id = customer_id
            search_request.query = query
            
            response = ga_service.search(request=search_request)
            
            # Log the results
            campaign_count = 0
            for row in response:
                campaign_count += 1
                logger.info(f"Campaign: {row.campaign.id} - {row.campaign.name}")
            
            logger.info(f"✅ Successfully retrieved {campaign_count} campaigns from Google Ads API")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to make API call: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in test_google_ads_connection: {str(e)}")
        return False

def fix_entrypoint_script():
    """Fix the Railway entrypoint script to properly pass environment variables"""
    logger.info("Checking for Railway entrypoint script issues...")
    
    # Check if we are in a Railway environment
    if not os.environ.get("RAILWAY_ENVIRONMENT"):
        logger.info("Not running in Railway environment, skipping entrypoint check")
        return False
    
    # Possible locations for entrypoint scripts
    entrypoint_files = [
        "/app/railway_entrypoint.sh",
        "/app/docker_entrypoint.sh",
        "./railway_entrypoint.sh",
        "./docker_entrypoint.sh"
    ]
    
    entrypoint_file = None
    for file in entrypoint_files:
        if os.path.exists(file):
            entrypoint_file = file
            logger.info(f"Found entrypoint script at {file}")
            break
    
    if not entrypoint_file:
        logger.error("❌ No entrypoint script found")
        return False
    
    # Read the entrypoint script
    try:
        with open(entrypoint_file, "r") as f:
            content = f.read()
        
        # Check if the script properly exports Google Ads variables
        google_ads_vars = [
            "GOOGLE_ADS_DEVELOPER_TOKEN",
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
            "GOOGLE_ADS_REFRESH_TOKEN",
            "GOOGLE_ADS_CUSTOMER_ID"
        ]
        
        missing_exports = []
        for var in google_ads_vars:
            if f"export {var}" not in content:
                missing_exports.append(var)
        
        if missing_exports:
            logger.warning(f"⚠️ Entrypoint script doesn't explicitly export: {missing_exports}")
            
            # Create a fix file that exports all variables
            fix_file = "fix_variables.sh"
            with open(fix_file, "w") as f:
                f.write("#!/bin/bash\n\n")
                f.write("# Script to fix environment variables\n")
                f.write("# Generated by debug_credentials.py\n\n")
                
                for var in google_ads_vars:
                    value = os.environ.get(var, "")
                    if value:
                        f.write(f'export {var}="{value}"\n')
                
                f.write("\necho \"Environment variables exported\"\n")
            
            # Make it executable
            os.chmod(fix_file, 0o755)
            logger.info(f"Created {fix_file} to export missing variables")
            
            # Try to source it
            os.system(f"source ./{fix_file}")
            logger.info(f"Sourced {fix_file}")
            
            return True
        else:
            logger.info("✅ Entrypoint script properly exports all Google Ads variables")
            return True
        
    except Exception as e:
        logger.error(f"❌ Error checking entrypoint script: {str(e)}")
        return False

def main():
    """Main function"""
    logger.info("Starting Google Ads credentials diagnostic")
    logger.info(f"Current time: {datetime.datetime.now().isoformat()}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Check if necessary packages are installed
    try:
        import yaml
    except ImportError:
        logger.info("Installing PyYAML...")
        os.system("pip install PyYAML")
    
    # Check environment variables
    missing_vars = check_environment_variables()
    
    # Check google-ads.yaml
    yaml_valid = check_google_ads_yaml()
    
    # Fix entrypoint script if needed
    fix_entrypoint_script()
    
    # Test Google Ads connection
    api_connection = test_google_ads_connection()
    
    # Final summary
    logger.info("\n===== DIAGNOSTIC SUMMARY =====")
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
    else:
        logger.info("✅ All environment variables are set")
    
    if yaml_valid:
        logger.info("✅ google-ads.yaml is valid")
    else:
        logger.error("❌ google-ads.yaml is invalid or missing")
    
    if api_connection:
        logger.info("✅ Successfully connected to Google Ads API")
    else:
        logger.error("❌ Failed to connect to Google Ads API")
    
    if not missing_vars and yaml_valid and api_connection:
        logger.info("✅ All checks passed! Google Ads API should work correctly.")
    else:
        logger.error("❌ Some checks failed. See logs for details.")

if __name__ == "__main__":
    main()
