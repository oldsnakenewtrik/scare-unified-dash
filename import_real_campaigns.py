"""
Script to import real campaign data from exported JSON files into the database.
This will ensure real campaign names are available for mapping.
"""
import os
import json
import logging
import sys
from datetime import datetime
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
logger = logging.getLogger("import_campaigns")

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")

def import_google_ads_data():
    """Import Google Ads data from JSON file to database"""
    data_file = 'data/google_ads_data_2025-03-12_to_2025-03-19_20250319_132330.json'
    
    try:
        # Read the JSON file
        with open(data_file, 'r') as file:
            campaigns_data = json.load(file)
        
        logger.info(f"Loaded {len(campaigns_data)} records from {data_file}")
        
        # Connect to the database
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # First clear existing Google Ads data to avoid duplicates
            conn.execute(text("DELETE FROM public.sm_fact_google_ads"))
            logger.info("Cleared existing Google Ads data")
            
            # Get unique campaign IDs and names for later reference
            unique_campaigns = {}
            for item in campaigns_data:
                campaign_id = str(item['campaign_id'])
                if campaign_id not in unique_campaigns:
                    unique_campaigns[campaign_id] = item['campaign_name']
            
            logger.info(f"Found {len(unique_campaigns)} unique campaigns")
            
            # Insert Google Ads data
            inserted_count = 0
            for item in campaigns_data:
                # Convert cost from micros if needed
                if 'cost' not in item and 'cost_micros' in item:
                    item['cost'] = float(item['cost_micros']) / 1000000
                
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
                    "cost": item['cost'],
                    "conversions": item['conversions']
                })
                
                inserted_count += 1
            
            # Verify which campaigns need mapping
            check_query = """
            SELECT DISTINCT 
                'Google Ads' as source_system,
                g.campaign_id as external_campaign_id,
                g.campaign_name as campaign_name
            FROM 
                sm_fact_google_ads g
            LEFT JOIN 
                sm_campaign_name_mapping m ON 
                CAST(g.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                m.source_system = 'Google Ads'
            WHERE 
                m.id IS NULL
            """
            
            unmapped = conn.execute(text(check_query)).fetchall()
            unmapped_campaigns = [dict(row._mapping) for row in unmapped]
            
            logger.info(f"Inserted {inserted_count} records into database")
            logger.info(f"Found {len(unmapped_campaigns)} unmapped campaigns that need mapping")
            
            # Display the campaign names that need mapping
            for i, campaign in enumerate(unmapped_campaigns[:10], 1):  # Show first 10
                logger.info(f"  {i}. {campaign['campaign_name']} (ID: {campaign['external_campaign_id']})")
            
            if len(unmapped_campaigns) > 10:
                logger.info(f"  ... and {len(unmapped_campaigns) - 10} more")
            
            conn.commit()
            logger.info("Database commit successful")
            
            return True
    except Exception as e:
        logger.error(f"Error importing Google Ads data: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting import of real campaign data")
    import_google_ads_data()
    logger.info("Import process completed")
