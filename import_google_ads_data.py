"""
Script to import real Google Ads campaign data into the database WITHOUT creating mappings.
This will allow manual mapping in the UI.
"""
import os
import json
import logging
import sys
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("import_google_ads")

# Load environment variables
load_dotenv()

# Get database URL from environment - use Railway URL
DATABASE_URL = os.getenv("RAILWAY_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

def check_database_health():
    """Check if we can connect to the database"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            logger.info(f"Database connection successful, received: {result}")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

def import_data_directly():
    """Import Google Ads data from JSON file to database directly using SQLAlchemy"""
    data_file = 'data/google_ads_data_2025-03-12_to_2025-03-19_20250319_132330.json'
    
    try:
        # Read the JSON file
        with open(data_file, 'r') as file:
            campaigns_data = json.load(file)
        
        logger.info(f"Loaded {len(campaigns_data)} records from {data_file}")
        
        # Connect to the database
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if fact table exists
            table_check = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sm_fact_google_ads')"
            )).scalar()
            
            if not table_check:
                logger.error("Table sm_fact_google_ads does not exist in the database")
                return False
            
            # Clear existing Google Ads data to avoid duplicates
            cleared = conn.execute(text("DELETE FROM public.sm_fact_google_ads"))
            logger.info(f"Cleared {cleared.rowcount} existing Google Ads records")
            
            # Insert new records
            inserted_count = 0
            for item in campaigns_data:
                # Convert cost from micros if needed
                if 'cost' not in item and 'cost_micros' in item:
                    cost = float(item['cost_micros']) / 1000000
                else:
                    cost = item.get('cost', 0)
                
                # Format the query with parameters
                insert_query = """
                INSERT INTO public.sm_fact_google_ads
                    (date, campaign_id, campaign_name, impressions, clicks, cost, conversions)
                VALUES
                    (:date, :campaign_id, :campaign_name, :impressions, :clicks, :cost, :conversions)
                """
                
                # Execute the insert
                conn.execute(text(insert_query), {
                    "date": item['date'],
                    "campaign_id": str(item['campaign_id']),
                    "campaign_name": item['campaign_name'],
                    "impressions": item['impressions'],
                    "clicks": item['clicks'],
                    "cost": cost,
                    "conversions": item.get('conversions', 0)
                })
                
                inserted_count += 1
                
                # Log progress every 20 records
                if inserted_count % 20 == 0:
                    logger.info(f"Inserted {inserted_count} records so far")
            
            # Log unique campaign stats
            unique_campaigns_query = """
            SELECT COUNT(DISTINCT campaign_id) as unique_count 
            FROM public.sm_fact_google_ads
            """
            unique_count = conn.execute(text(unique_campaigns_query)).scalar()
            
            # Get examples of inserted campaigns
            examples_query = """
            SELECT DISTINCT campaign_id, campaign_name 
            FROM public.sm_fact_google_ads 
            LIMIT 5
            """
            examples = conn.execute(text(examples_query)).fetchall()
            example_campaigns = [f"{row._mapping['campaign_name']} (ID: {row._mapping['campaign_id']})" for row in examples]
            
            conn.commit()
            logger.info(f"Successfully inserted {inserted_count} Google Ads records with {unique_count} unique campaigns")
            logger.info(f"Example campaigns: {example_campaigns}")
            
            return True
    except Exception as e:
        logger.error(f"Error importing Google Ads data: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Google Ads data import process")
    
    # First check database connection
    if check_database_health():
        # If database is healthy, proceed with import
        logger.info("Database connection successful, proceeding with data import")
        success = import_data_directly()
        if success:
            logger.info("Google Ads data import completed successfully")
        else:
            logger.error("Google Ads data import failed")
    else:
        logger.error("Database connection failed, aborting import")
    
    logger.info("Import process completed")
