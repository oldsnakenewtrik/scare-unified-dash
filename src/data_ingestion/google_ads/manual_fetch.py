#!/usr/bin/env python

"""
Manual Google Ads data fetch script.
This script will fetch data from Google Ads API and save it to the database.
It can be run manually or as a scheduled job.
"""

import os
import sys
import logging
import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("manual_fetch.log")
    ]
)
logger = logging.getLogger("manual_fetch")

# Function to run a Python script and capture output
def run_script(script_path, script_name):
    """Run a Python script and capture output"""
    logger.info(f"Running {script_name}...")
    
    full_path = Path(script_path)
    if not full_path.exists():
        logger.error(f"Script not found: {full_path}")
        return False
    
    try:
        # Import and run the script directly
        sys.path.insert(0, str(full_path.parent))
        
        # Dynamic import based on filename without extension
        module_name = full_path.stem
        
        # Check if module is already imported
        if module_name in sys.modules:
            # Remove the module to reload it
            logger.info(f"Reloading module {module_name}")
            del sys.modules[module_name]
        
        # Now import the module
        logger.info(f"Importing module {module_name} from {full_path}")
        __import__(module_name)
        
        logger.info(f"{script_name} completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running {script_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_credentials():
    """Check if Google Ads credentials are set"""
    missing = []
    
    credentials = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID"
    ]
    
    for cred in credentials:
        if not os.environ.get(cred):
            missing.append(cred)
    
    if missing:
        logger.error(f"Missing credentials: {missing}")
        return False
    
    logger.info("All Google Ads credentials are set")
    return True

def main():
    """Main function to run the ETL process"""
    logger.info("=== Starting manual Google Ads data fetch ===")
    
    # Check credentials
    if not check_credentials():
        logger.error("Credentials check failed. Please set all required environment variables.")
        return False
    
    # Step 1: Run the debug script to verify credentials
    debug_script = Path(__file__).parent / "debug_credentials.py"
    if not run_script(debug_script, "Credentials debug script"):
        logger.error("Failed to verify credentials. Check debug_credentials.py output.")
        return False
    
    # Step 2: Fetch data from Google Ads API
    fetch_script = Path(__file__).parent / "fetch_to_json.py"
    if not run_script(fetch_script, "Google Ads fetch script"):
        logger.error("Failed to fetch Google Ads data. Check fetch_to_json.py output.")
        return False
    
    # Step 3: Import data to the database
    import_script = Path(__file__).parent / "import_from_json.py"
    if not run_script(import_script, "Database import script"):
        logger.error("Failed to import data to database. Check import_from_json.py output.")
        return False
    
    logger.info("=== Manual Google Ads data fetch completed successfully ===")
    return True

if __name__ == "__main__":
    success = main()
    
    if success:
        logger.info("ETL process completed successfully")
        sys.exit(0)
    else:
        logger.error("ETL process failed")
        sys.exit(1)
