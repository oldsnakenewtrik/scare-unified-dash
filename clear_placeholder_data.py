"""
Script to clear placeholder data from the SCARE Unified Dashboard database.
This will remove:
1. Campaign mappings for non-Google Ads sources
2. Sample data from non-Google Ads fact tables
"""
import logging
import sys
import os
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
logger = logging.getLogger("clear_placeholder")

# Load environment variables
load_dotenv()

# Get database URL from environment - add more fallbacks
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL") or "postgresql://scare_user:scare_password@postgres:5432/scare_metrics"

def clear_placeholder_data():
    """Remove placeholder data from the database"""
    try:
        # Print database URL for debugging (masking password)
        debug_url = DATABASE_URL
        if "://" in debug_url:
            parts = debug_url.split("://")
            if "@" in parts[1]:
                userpass, hostdb = parts[1].split("@", 1)
                if ":" in userpass:
                    user, password = userpass.split(":", 1)
                    debug_url = f"{parts[0]}://{user}:****@{hostdb}"
        
        logger.info(f"Connecting to database: {debug_url}")
        
        # Connect to database
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Begin transaction
            trans = conn.begin()
            
            try:
                # 1. Remove non-Google Ads campaign mappings
                logger.info("Removing non-Google Ads campaign mappings...")
                remove_mapping_query = """
                DELETE FROM public.sm_campaign_name_mapping
                WHERE source_system != 'Google Ads'
                """
                result = conn.execute(text(remove_mapping_query))
                logger.info(f"Removed {result.rowcount} non-Google Ads campaign mappings")
                
                # 2. Clear data from other fact tables
                tables_to_clear = ['sm_fact_bing_ads', 'sm_fact_redtrack', 'sm_fact_matomo']
                
                for table in tables_to_clear:
                    logger.info(f"Clearing data from {table}...")
                    try:
                        clear_query = f"DELETE FROM public.{table}"
                        result = conn.execute(text(clear_query))
                        logger.info(f"Removed {result.rowcount} rows from {table}")
                    except Exception as e:
                        logger.warning(f"Error clearing {table}: {str(e)}")
                
                # Commit the transaction
                trans.commit()
                logger.info("All placeholder data successfully removed")
                
            except Exception as e:
                # Rollback in case of error
                trans.rollback()
                logger.error(f"Error clearing placeholder data: {str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

if __name__ == "__main__":
    clear_placeholder_data()
