import os
import sys
import logging
import psycopg2
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def execute_query(conn, query):
    """Execute a query and return all results."""
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()

def main():
    # Get database connection from environment variables
    db_url = os.environ.get("DATABASE_URL")
    
    if not db_url:
        # Use the public URL from Railway for external access
        db_url = "postgresql://postgres:HGnALEQyXYobjgWixRVpnfQBVXcfTXoF@nozomi.proxy.rlwy.net:11923/railway"
        
        # Alternatively try Railway specific environment variables
        if not db_url:
            host = os.environ.get("PGHOST", "localhost")
            port = os.environ.get("PGPORT", "5432")
            user = os.environ.get("PGUSER", "postgres")
            password = os.environ.get("PGPASSWORD", "postgres")
            dbname = os.environ.get("PGDATABASE", "postgres")
            
            # Build connection string
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    # Mask the password for logging
    parsed_url = urlparse(db_url)
    masked_url = f"{parsed_url.scheme}://{parsed_url.username}:****@{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
    logger.info(f"Connecting to database: {masked_url}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        logger.info("Connected to database successfully")
        
        # Check if views exist
        views_query = """
        SELECT table_name FROM information_schema.views 
        WHERE table_schema = 'public' AND 
        table_name IN ('sm_unified_ads_metrics', 'sm_campaign_performance');
        """
        views = execute_query(conn, views_query)
        logger.info(f"Found views: {views}")
        
        # Check view definitions
        for view in views:
            view_name = view[0]
            logger.info(f"Checking view definition for {view_name}")
            view_def_query = f"""
            SELECT view_definition FROM information_schema.views 
            WHERE table_schema = 'public' AND table_name = '{view_name}';
            """
            view_def = execute_query(conn, view_def_query)
            if view_def and view_def[0]:
                logger.info(f"View definition: {view_def[0][0][:100]}...") # Show first 100 chars
            else:
                logger.warning(f"No view definition found for {view_name}")
        
        # Check if Google Ads data exists
        google_ads_query = "SELECT COUNT(*) FROM public.sm_fact_google_ads;"
        google_ads_count = execute_query(conn, google_ads_query)
        logger.info(f"Google Ads data count: {google_ads_count[0][0]}")
        
        # Check data in the unified metrics view
        unified_query = "SELECT COUNT(*) FROM public.sm_unified_ads_metrics;"
        try:
            unified_count = execute_query(conn, unified_query)
            logger.info(f"Unified metrics data count: {unified_count[0][0]}")
        except Exception as e:
            logger.error(f"Error querying unified metrics view: {e}")
        
        # Check data in the campaign performance view
        performance_query = "SELECT COUNT(*) FROM public.sm_campaign_performance;"
        try:
            performance_count = execute_query(conn, performance_query)
            logger.info(f"Campaign performance data count: {performance_count[0][0]}")
        except Exception as e:
            logger.error(f"Error querying campaign performance view: {e}")
        
        # If no data in views but data exists in Google Ads table, create views
        if google_ads_count[0][0] > 0:
            logger.info("Creating or updating views...")
            
            # Create unified metrics view
            unified_view_sql = """
            CREATE OR REPLACE VIEW public.sm_unified_ads_metrics AS
            SELECT 
                'google_ads' as platform,
                COALESCE(g.network, 'Unknown') as network,
                g.date,
                g.campaign_id,
                g.campaign_name,
                g.campaign_name as original_campaign_name,
                'Unknown' as pretty_network,
                'Google Ads' as pretty_source,
                'Uncategorized' as campaign_category,
                'Uncategorized' as campaign_type,
                g.impressions,
                g.clicks,
                g.cost,
                g.conversions,
                CASE WHEN g.impressions > 0 THEN g.clicks::FLOAT / g.impressions ELSE 0 END as ctr,
                CASE WHEN g.clicks > 0 THEN g.conversions::FLOAT / g.clicks ELSE 0 END as conversion_rate,
                CASE WHEN g.conversions > 0 THEN g.cost / g.conversions ELSE 0 END as cost_per_conversion
            FROM 
                public.sm_fact_google_ads g;
            """
            try:
                with conn.cursor() as cur:
                    cur.execute(unified_view_sql)
                conn.commit()
                logger.info("Unified metrics view created successfully")
            except Exception as e:
                logger.error(f"Error creating unified metrics view: {e}")
                conn.rollback()
            
            # Create campaign performance view
            performance_view_sql = """
            CREATE OR REPLACE VIEW public.sm_campaign_performance AS
            SELECT
                platform,
                network,
                campaign_id,
                campaign_name,
                original_campaign_name,
                pretty_network,
                pretty_source,
                campaign_category,
                campaign_type,
                date,
                SUM(impressions) as impressions,
                SUM(clicks) as clicks,
                SUM(cost) as cost,
                SUM(conversions) as conversions,
                CASE WHEN SUM(impressions) > 0 THEN SUM(clicks)::FLOAT / SUM(impressions) ELSE 0 END as ctr,
                CASE WHEN SUM(clicks) > 0 THEN SUM(conversions)::FLOAT / SUM(clicks) ELSE 0 END as conversion_rate,
                CASE WHEN SUM(conversions) > 0 THEN SUM(cost) / SUM(conversions) ELSE 0 END as cost_per_conversion
            FROM 
                public.sm_unified_ads_metrics
            GROUP BY
                platform,
                network,
                campaign_id,
                campaign_name,
                original_campaign_name,
                pretty_network,
                pretty_source,
                campaign_category,
                campaign_type,
                date;
            """
            try:
                with conn.cursor() as cur:
                    cur.execute(performance_view_sql)
                conn.commit()
                logger.info("Campaign performance view created successfully")
            except Exception as e:
                logger.error(f"Error creating campaign performance view: {e}")
                conn.rollback()
            
            # Check data in views after creation
            try:
                unified_count = execute_query(conn, unified_query)
                logger.info(f"Unified metrics data count after view creation: {unified_count[0][0]}")
                
                performance_count = execute_query(conn, performance_query)
                logger.info(f"Campaign performance data count after view creation: {performance_count[0][0]}")
            except Exception as e:
                logger.error(f"Error querying views after creation: {e}")
        
        # Close the connection
        conn.close()
        logger.info("Database connection closed")
        
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
