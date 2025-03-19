#!/usr/bin/env python

"""
Script to add real Google Ads campaign data from a JSON file to the Railway database.
Use this when you need to force campaign data into the system.
"""

import os
import sys
import json
import logging
from pathlib import Path
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("add_real_campaigns.log")
    ]
)
logger = logging.getLogger("add_real_campaigns")

# Load environment variables
load_dotenv()

def get_db_engine():
    """Get SQLAlchemy engine for database connection"""
    try:
        # Try to get DATABASE_URL from environment
        db_url = os.getenv("RAILWAY_DATABASE_URL", os.getenv("DATABASE_URL"))
        if not db_url:
            logger.error("DATABASE_URL environment variable not set")
            return None
        
        logger.info(f"Connecting to database at: {db_url}")
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        logger.error(f"Error creating database engine: {str(e)}")
        return None

def check_api_health():
    """Check if the API is healthy"""
    try:
        api_url = "https://scare-unified-dash-production.up.railway.app/health"
        logger.info(f"Checking API health at {api_url}")
        
        response = requests.get(api_url)
        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"API is healthy: {health_data}")
            return True
        else:
            logger.error(f"API health check failed with status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error checking API health: {str(e)}")
        return False

def check_unmapped_campaigns():
    """Check for unmapped campaigns"""
    try:
        api_url = "https://scare-unified-dash-production.up.railway.app/api/unmapped-campaigns"
        logger.info(f"Checking unmapped campaigns at {api_url}")
        
        response = requests.get(api_url)
        if response.status_code == 200:
            campaigns = response.json()
            logger.info(f"Found {len(campaigns)} unmapped campaigns")
            
            # Show a few examples if available
            if campaigns:
                logger.info("Examples of unmapped campaigns:")
                for i, campaign in enumerate(campaigns[:5]):
                    logger.info(f"{i+1}. {campaign.get('source_system')}: {campaign.get('campaign_name')}")
            else:
                logger.warning("No unmapped campaigns found")
                
            return campaigns
        else:
            logger.error(f"Failed to get unmapped campaigns: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error checking unmapped campaigns: {str(e)}")
        return []

def clear_google_ads_mappings(engine):
    """Clear all Google Ads campaign mappings"""
    logger.info("Clearing Google Ads campaign mappings")
    
    try:
        with Session(engine) as session:
            # Check if there are any mappings to clear
            check_query = text("SELECT COUNT(*) FROM sm_campaign_name_mapping WHERE source_system = 'Google Ads'")
            count = session.execute(check_query).scalar() or 0
            logger.info(f"Found {count} existing Google Ads mappings")
            
            if count == 0:
                logger.info("No Google Ads mappings to clear")
                return True
            
            # Delete all Google Ads mappings
            delete_query = text("DELETE FROM sm_campaign_name_mapping WHERE source_system = 'Google Ads'")
            result = session.execute(delete_query)
            session.commit()
            
            logger.info(f"Deleted {result.rowcount} Google Ads mappings")
            return True
    except Exception as e:
        logger.error(f"Error clearing Google Ads mappings: {str(e)}")
        return False

def import_campaign_data(engine, data_file):
    """Import Google Ads campaign data from a JSON file"""
    logger.info(f"Importing campaign data from {data_file}")
    
    try:
        # Load the data from the JSON file
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} records from {data_file}")
        
        # Start a session
        with Session(engine) as session:
            # Clear existing Google Ads data
            clear_query = text("DELETE FROM sm_fact_google_ads")
            session.execute(clear_query)
            logger.info("Cleared existing Google Ads data")
            
            # Insert each record
            inserted = 0
            for item in data:
                # Create the INSERT query
                insert_query = text("""
                INSERT INTO sm_fact_google_ads 
                (date, campaign_id, campaign_name, impressions, clicks, cost, conversions)
                VALUES 
                (:date, :campaign_id, :campaign_name, :impressions, :clicks, :cost, :conversions)
                """)
                
                # Execute the query with parameters
                session.execute(insert_query, {
                    "date": item.get("date"),
                    "campaign_id": str(item.get("campaign_id")),
                    "campaign_name": item.get("campaign_name"),
                    "impressions": item.get("impressions", 0),
                    "clicks": item.get("clicks", 0),
                    "cost": float(item.get("cost", 0)),
                    "conversions": item.get("conversions", 0)
                })
                
                inserted += 1
            
            # Commit the changes
            session.commit()
            logger.info(f"Inserted {inserted} records into the database")
            
            # Check for unique campaigns
            unique_query = text("SELECT COUNT(DISTINCT campaign_id) FROM sm_fact_google_ads")
            unique_count = session.execute(unique_query).scalar() or 0
            logger.info(f"Number of unique campaigns: {unique_count}")
            
            # Show a few examples
            examples_query = text("SELECT DISTINCT campaign_id, campaign_name FROM sm_fact_google_ads LIMIT 5")
            examples = session.execute(examples_query).fetchall()
            
            logger.info("Examples of imported campaigns:")
            for i, example in enumerate(examples):
                logger.info(f"{i+1}. {example.campaign_id}: {example.campaign_name}")
            
            return True
    except Exception as e:
        logger.error(f"Error importing campaign data: {str(e)}")
        return False

def run_admin_command(command, json_file=None):
    """Run an admin command on the Railway app"""
    try:
        endpoint = f"https://scare-unified-dash-production.up.railway.app/api/admin/{command}"
        
        if json_file:
            # Read the JSON file
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            # Send the data to the admin endpoint
            response = requests.post(endpoint, json=data)
        else:
            # Just call the endpoint without data
            response = requests.post(endpoint)
            
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Admin command {command} executed successfully: {result}")
            return True
        else:
            logger.error(f"Admin command {command} failed with status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error running admin command {command}: {str(e)}")
        return False

def main():
    """Main function"""
    logger.info("Starting add_real_campaigns script")
    
    # Check if we're trying to deploy the admin commands
    if len(sys.argv) > 1 and sys.argv[1] == "--deploy-admin":
        logger.info("Deploying admin commands")
        deploy_admin_commands()
        return
    
    # Get the database engine
    engine = get_db_engine()
    if not engine:
        logger.error("Failed to get database engine")
        return
    
    # Check the API health
    api_healthy = check_api_health()
    if not api_healthy:
        logger.warning("API is not healthy, but continuing anyway")
    
    # Check for data file
    data_file = None
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        # Look for JSON files in the data directory
        data_dir = Path("data")
        json_files = list(data_dir.glob("google_ads_data_*.json"))
        
        if json_files:
            # Use the newest file
            data_file = str(max(json_files, key=lambda f: f.stat().st_mtime))
            logger.info(f"Using newest data file: {data_file}")
        else:
            logger.error("No data file specified and no .json files found in data directory")
            return
    
    # Clear Google Ads mappings
    clear_success = clear_google_ads_mappings(engine)
    if not clear_success:
        logger.warning("Failed to clear Google Ads mappings, but continuing")
    
    # Import campaign data
    import_success = import_campaign_data(engine, data_file)
    if not import_success:
        logger.error("Failed to import campaign data")
        return
    
    # Check for unmapped campaigns
    unmapped = check_unmapped_campaigns()
    if not unmapped:
        logger.warning("No unmapped campaigns found after import")
    
    logger.info("Campaign data import completed successfully")

def deploy_admin_commands():
    """Deploy admin commands to Railway"""
    try:
        # Get the current directory
        current_dir = Path(__file__).parent
        
        # Check if we have the admin_commands.py file
        admin_file = current_dir / "admin_commands.py"
        if not admin_file.exists():
            logger.error(f"Admin commands file not found at {admin_file}")
            return False
        
        # Check if main.py exists
        main_file = current_dir / "main.py"
        if not main_file.exists():
            logger.error(f"Main API file not found at {main_file}")
            return False
        
        # First, back up the main.py file
        backup_file = current_dir / "main.py.bak"
        with open(main_file, 'r') as f:
            main_content = f.read()
        
        with open(backup_file, 'w') as f:
            f.write(main_content)
        
        logger.info(f"Backed up {main_file} to {backup_file}")
        
        # Add the admin commands to main.py
        with open(admin_file, 'r') as f:
            admin_content = f.read()
        
        # Add the new imports and endpoints to main.py
        admin_import = "\nfrom admin_commands import clear_google_ads_mappings, import_real_google_ads_data\n"
        admin_endpoints = '''
@app.post("/api/admin/clear_google_ads_mappings")
def admin_clear_google_ads_mappings(db=Depends(get_db)):
    """Clear all Google Ads campaign mappings"""
    logger.info("Admin endpoint: clear_google_ads_mappings called")
    success = clear_google_ads_mappings(db)
    return {"success": success}

@app.post("/api/admin/import_real_google_ads_data")
def admin_import_real_google_ads_data(data: dict = Body(None), db=Depends(get_db)):
    """Import real Google Ads data"""
    logger.info("Admin endpoint: import_real_google_ads_data called")
    success = import_real_google_ads_data(db, data)
    return {"success": success}
'''
        
        # Insert the admin import after the last import statement
        import_end = main_content.rfind("import")
        import_end = main_content.find("\n", import_end)
        modified_content = main_content[:import_end + 1] + admin_import + main_content[import_end + 1:]
        
        # Insert the admin endpoints before the if __name__ == "__main__"
        main_end = modified_content.find('if __name__ == "__main__"')
        if main_end == -1:
            # If we can't find that, insert at the end
            modified_content += "\n" + admin_endpoints
        else:
            modified_content = modified_content[:main_end] + admin_endpoints + modified_content[main_end:]
        
        # Write the modified content back to main.py
        with open(main_file, 'w') as f:
            f.write(modified_content)
        
        logger.info(f"Modified {main_file} to include admin endpoints")
        
        # Write the admin_commands.py file
        with open(admin_file, 'w') as f:
            f.write(admin_content)
        
        logger.info(f"Created/updated {admin_file}")
        
        # Commit the changes to git
        os.system("git add src/api/main.py src/api/admin_commands.py")
        os.system('git commit -m "Add admin commands for campaign management"')
        os.system("git push")
        
        logger.info("Changes committed and pushed to git")
        
        return True
    except Exception as e:
        logger.error(f"Error deploying admin commands: {str(e)}")
        return False

if __name__ == "__main__":
    main()
