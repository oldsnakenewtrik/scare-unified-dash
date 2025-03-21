#!/usr/bin/env python
"""
Post-deployment script to run after the application starts.
This ensures the database views are always up-to-date.
"""
import logging
import sys
import time
from src.api.db_init import create_or_update_views, init_database
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("post_deploy.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("post_deploy")

# Load environment variables
load_dotenv()

def get_db_engine():
    """
    Create and return a SQLAlchemy database engine using Railway PostgreSQL variables
    """
    # Check for Railway postgres variables first
    postgres_host = os.getenv('PGHOST', 'postgres.railway.internal')
    postgres_port = os.getenv('PGPORT', '5432')
    postgres_user = os.getenv('PGUSER', 'postgres')
    postgres_password = os.getenv('PGPASSWORD')
    postgres_db = os.getenv('PGDATABASE', 'railway')
    
    # Fallback to generic DATABASE_URL if specific variables aren't available
    database_url = os.getenv('DATABASE_URL')
    railway_database_url = os.getenv('RAILWAY_DATABASE_URL')
    
    # Log connection attempt for debugging
    logger.info("Attempting to create database engine...")
    
    if postgres_password and postgres_host:
        # Construct connection string
        connection_string = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
        logger.info(f"Creating database engine with Railway PostgreSQL variables (host: {postgres_host})")
        return create_engine(connection_string)
    elif railway_database_url:
        logger.info("Creating database engine with RAILWAY_DATABASE_URL environment variable")
        return create_engine(railway_database_url)
    elif database_url:
        logger.info("Creating database engine with DATABASE_URL environment variable")
        return create_engine(database_url)
    else:
        logger.error("No database connection information found in environment variables")
        # Print available environment variables for debugging
        logger.info("Available environment variables:")
        for key in os.environ:
            if "DATABASE" in key or "PG" in key or "SQL" in key:
                logger.info(f"  - {key}: {'*' * min(len(os.environ[key]), 5)}")
        return None

def verify_google_ads_data():
    """Verify that Google Ads data is properly accessible"""
    try:
        # Connect to database
        engine = get_db_engine()
        
        if not engine:
            logger.error("Failed to create database engine")
            return False
        
        with engine.connect() as conn:
            # Check Google Ads data
            google_ads_result = conn.execute(text("""
                SELECT COUNT(*) FROM public.sm_fact_google_ads
            """)).scalar()
            
            logger.info(f"Found {google_ads_result} rows in Google Ads fact table")
            
            # Check if data appears in the unified view
            unified_result = conn.execute(text("""
                SELECT COUNT(*) FROM public.sm_unified_ads_metrics 
                WHERE platform = 'google_ads'
            """)).scalar()
            
            logger.info(f"Found {unified_result} rows in unified metrics view for Google Ads")
            
            # Check if data appears in the performance view
            performance_result = conn.execute(text("""
                SELECT COUNT(*) FROM public.sm_campaign_performance 
                WHERE platform = 'google_ads'
            """)).scalar()
            
            logger.info(f"Found {performance_result} rows in campaign performance view for Google Ads")
            
            # Return true if data is found in the performance view
            return performance_result > 0
        
    except Exception as e:
        logger.error(f"Error verifying Google Ads data: {str(e)}")
        return False

def main():
    """Main function for post-deployment tasks"""
    try:
        logger.info("Starting post-deployment tasks")
        
        # Wait a short time to ensure database is fully up
        logger.info("Waiting for database to be fully available...")
        time.sleep(5)
        
        # Attempt to connect to the database and create/update views
        retries = 5
        success = False
        
        for attempt in range(1, retries + 1):
            logger.info(f"Database connection attempt {attempt}/{retries}")
            
            # Connect to database
            engine = get_db_engine()
            
            if not engine:
                logger.warning(f"Failed to create database engine on attempt {attempt}")
                if attempt < retries:
                    time.sleep(5)
                continue
            
            try:
                with engine.connect() as conn:
                    logger.info("Database connection successful")
                    
                    # Ensure all tables and columns exist
                    logger.info("Initializing database if needed")
                    init_database()
                    
                    # Create or update views
                    logger.info("Creating or updating database views")
                    create_or_update_views(conn)
                    
                    # Verify Google Ads data is accessible
                    if verify_google_ads_data():
                        logger.info("Google Ads data verified successfully")
                    else:
                        logger.warning("Google Ads data verification failed - views exist but data may not be accessible")
                
                success = True
                break
                
            except Exception as e:
                logger.error(f"Database operation failed on attempt {attempt}: {str(e)}")
                if attempt < retries:
                    time.sleep(5)
        
        if success:
            logger.info("✅ Post-deployment tasks completed successfully")
            return 0
        else:
            logger.error("❌ Post-deployment tasks failed after multiple attempts")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error in post-deployment tasks: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
