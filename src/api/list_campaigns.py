#!/usr/bin/env python

import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("campaign_lister")

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("RAILWAY_DATABASE_URL", os.getenv("DATABASE_URL"))

def list_campaigns():
    """List all campaigns in the database"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # List mapped campaigns
            logger.info("=== MAPPED CAMPAIGNS ===")
            mapped_query = """
            SELECT 
                m.id, 
                m.source_system, 
                m.external_campaign_id, 
                m.original_campaign_name, 
                m.pretty_campaign_name,
                m.campaign_category,
                m.campaign_type,
                m.network
            FROM 
                sm_campaign_name_mapping m
            ORDER BY 
                m.source_system, m.original_campaign_name
            """
            mapped_results = conn.execute(text(mapped_query)).fetchall()
            logger.info(f"Found {len(mapped_results)} mapped campaigns")
            
            for i, row in enumerate(mapped_results):
                r = row._mapping
                logger.info(f"{i+1}. [{r['source_system']}] {r['original_campaign_name']} -> " +
                          f"{r['pretty_campaign_name']} (Category: {r['campaign_category']}, " +
                          f"Type: {r['campaign_type']}, Network: {r['network']})")
            
            # Count campaigns in each fact table
            logger.info("\n=== CAMPAIGN COUNTS BY SOURCE ===")
            for table in ["sm_fact_google_ads", "sm_fact_bing_ads", "sm_fact_matomo", "sm_fact_redtrack"]:
                count_query = f"SELECT COUNT(DISTINCT campaign_id) FROM {table}"
                count = conn.execute(text(count_query)).scalar() or 0
                logger.info(f"{table}: {count} unique campaigns")

            # List actual campaigns in each fact table
            logger.info("\n=== UNIQUE CAMPAIGNS IN FACT TABLES ===")
            for source, table in [
                ("Google Ads", "sm_fact_google_ads"),
                ("Bing Ads", "sm_fact_bing_ads"),
                ("RedTrack", "sm_fact_redtrack"),
                ("Matomo", "sm_fact_matomo")
            ]:
                logger.info(f"\n{source} campaigns:")
                campaigns_query = f"""
                SELECT DISTINCT campaign_id, campaign_name 
                FROM {table}
                ORDER BY campaign_name
                """
                campaigns = conn.execute(text(campaigns_query)).fetchall()
                if campaigns:
                    for i, camp in enumerate(campaigns):
                        logger.info(f"{i+1}. ID: {camp._mapping['campaign_id']} - Name: {camp._mapping['campaign_name']}")
                else:
                    logger.info("No campaigns found")

    except Exception as e:
        logger.error(f"Error listing campaigns: {str(e)}")
        return False

if __name__ == "__main__":
    list_campaigns()
