#!/usr/bin/env python
"""
Script to refresh database views and ensure Google Ads data is properly linked
"""
import sys
import logging
from src.api.db_init import create_or_update_views
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("refresh_views")

# Load environment variables
load_dotenv()

def get_db_engine():
    """
    Create and return a SQLAlchemy database engine using Railway PostgreSQL variables
    """
    # Check for Railway postgres variables first
    postgres_host = os.getenv('PGHOST', 'localhost')
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

def main():
    """Main function to refresh views and check Google Ads data"""
    try:
        # Connect to database
        engine = get_db_engine()
        
        if not engine:
            logger.error("Failed to create database engine")
            return 1
        
        with engine.connect() as conn:
            # Refresh views
            create_or_update_views(conn)
            
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
            
            # Check mappings
            mapping_result = conn.execute(text("""
                SELECT COUNT(*) FROM public.sm_campaign_name_mapping 
                WHERE source_system = 'Google Ads' AND is_active = TRUE
            """)).scalar()
            
            logger.info(f"Found {mapping_result} active campaign mappings for Google Ads")
            
            # Check recent data
            recent_result = conn.execute(text("""
                SELECT date, SUM(impressions) as impressions, SUM(clicks) as clicks, SUM(cost) as cost
                FROM public.sm_campaign_performance 
                WHERE platform = 'google_ads'
                GROUP BY date
                ORDER BY date DESC
                LIMIT 7
            """))
            
            logger.info("Recent Google Ads metrics:")
            for row in recent_result:
                date_str = row[0].strftime('%Y-%m-%d')
                logger.info(f"  {date_str}: Impressions={row[1]}, Clicks={row[2]}, Cost=${row[3]:.2f}")
        
        logger.info("✅ Views refreshed successfully")
        print("✅ Database views refreshed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error refreshing views: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
