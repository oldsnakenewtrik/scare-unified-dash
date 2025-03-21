"""
Script to fix Railway database views for the SCARE Unified Dashboard
Uses psycopg2 to connect directly to Railway PostgreSQL database with hardcoded credentials
"""
import os
import sys
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor
except ImportError:
    logger.error("psycopg2 is required. Install it with: pip install psycopg2-binary")
    sys.exit(1)

# CONNECTION DETAILS (extracted from Railway CLI)
DB_HOST = "nozomi.proxy.rlwy.net"
DB_PORT = "11923"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASSWORD = "HGnALEQyXYobjgWixRVpnfQBVXcfTXoF"

# SQL for recreating the views
UNIFIED_VIEW_SQL = """
CREATE OR REPLACE VIEW public.sm_unified_ads_metrics AS
SELECT 
    'google_ads' as platform,
    COALESCE(g.network, 'Unknown') as network,
    g.date,
    g.campaign_id,
    COALESCE(m.pretty_campaign_name, g.campaign_name) as campaign_name,
    g.campaign_name as original_campaign_name,
    COALESCE(m.pretty_network, 'Unknown') as pretty_network,
    COALESCE(m.pretty_source, 'Google Ads') as pretty_source,
    COALESCE(m.campaign_category, 'Uncategorized') as campaign_category,
    COALESCE(m.campaign_type, 'Uncategorized') as campaign_type,
    g.impressions,
    g.clicks,
    g.cost,
    g.conversions,
    CASE 
        WHEN g.impressions > 0 THEN g.clicks::FLOAT / g.impressions 
        ELSE 0 
    END as ctr,
    CASE 
        WHEN g.clicks > 0 THEN g.conversions::FLOAT / g.clicks 
        ELSE 0 
    END as conversion_rate,
    CASE 
        WHEN g.conversions > 0 THEN g.cost / g.conversions 
        ELSE 0 
    END as cost_per_conversion
FROM 
    public.sm_fact_google_ads g
LEFT JOIN 
    public.sm_campaign_name_mapping m ON m.source_system = 'Google Ads' 
        AND m.external_campaign_id = g.campaign_id::VARCHAR
        AND m.is_active = TRUE

UNION ALL

SELECT 
    'bing_ads' as platform,
    COALESCE(b.network, 'Unknown') as network,
    b.date,
    b.campaign_id,
    COALESCE(m.pretty_campaign_name, b.campaign_name) as campaign_name,
    b.campaign_name as original_campaign_name,
    COALESCE(m.pretty_network, 'Unknown') as pretty_network,
    COALESCE(m.pretty_source, 'Bing Ads') as pretty_source,
    COALESCE(m.campaign_category, 'Uncategorized') as campaign_category,
    COALESCE(m.campaign_type, 'Uncategorized') as campaign_type,
    b.impressions,
    b.clicks,
    b.cost,
    b.conversions,
    CASE 
        WHEN b.impressions > 0 THEN b.clicks::FLOAT / b.impressions 
        ELSE 0 
    END as ctr,
    CASE 
        WHEN b.clicks > 0 THEN b.conversions::FLOAT / b.clicks 
        ELSE 0 
    END as conversion_rate,
    CASE 
        WHEN b.conversions > 0 THEN b.cost / b.conversions 
        ELSE 0 
    END as cost_per_conversion
FROM 
    public.sm_fact_bing_ads b
LEFT JOIN 
    public.sm_campaign_name_mapping m ON m.source_system = 'Bing Ads' 
        AND m.external_campaign_id = b.campaign_id::VARCHAR
        AND m.is_active = TRUE

UNION ALL

SELECT 
    'redtrack' as platform,
    COALESCE(r.network, 'Affiliate') as network,
    r.date,
    r.campaign_id,
    COALESCE(m.pretty_campaign_name, r.campaign_name) as campaign_name,
    r.campaign_name as original_campaign_name,
    COALESCE(m.pretty_network, 'Unknown') as pretty_network,
    COALESCE(m.pretty_source, 'RedTrack') as pretty_source,
    COALESCE(m.campaign_category, 'Uncategorized') as campaign_category,
    COALESCE(m.campaign_type, 'Uncategorized') as campaign_type,
    0 as impressions,
    r.clicks,
    r.cost,
    r.conversions,
    0 as ctr,
    CASE 
        WHEN r.clicks > 0 THEN r.conversions::FLOAT / r.clicks 
        ELSE 0 
    END as conversion_rate,
    CASE 
        WHEN r.conversions > 0 THEN r.cost / r.conversions 
        ELSE 0 
    END as cost_per_conversion
FROM 
    public.sm_fact_redtrack r
LEFT JOIN 
    public.sm_campaign_name_mapping m ON m.source_system = 'RedTrack' 
        AND m.external_campaign_id = r.campaign_id::VARCHAR
        AND m.is_active = TRUE;
"""

PERFORMANCE_VIEW_SQL = """
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
    CASE 
        WHEN SUM(impressions) > 0 THEN SUM(clicks)::FLOAT / SUM(impressions) 
        ELSE 0 
    END as ctr,
    CASE 
        WHEN SUM(clicks) > 0 THEN SUM(conversions)::FLOAT / SUM(clicks) 
        ELSE 0 
    END as conversion_rate,
    CASE 
        WHEN SUM(conversions) > 0 THEN SUM(cost) / SUM(conversions) 
        ELSE 0 
    END as cost_per_conversion
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

# Diagnostic queries
DIAGNOSTIC_QUERIES = {
    "tables": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;",
    "google_ads_count": "SELECT COUNT(*) FROM public.sm_fact_google_ads;",
    "network_distribution": "SELECT network, COUNT(*) FROM public.sm_fact_google_ads GROUP BY network ORDER BY COUNT(*) DESC;",
    "views": "SELECT table_name FROM information_schema.views WHERE table_schema = 'public';",
    "mappings": "SELECT COUNT(*) FROM public.sm_campaign_name_mapping WHERE source_system = 'Google Ads';",
    "unified_data": "SELECT platform, COUNT(*) FROM public.sm_unified_ads_metrics GROUP BY platform;",
    "google_unified_data": "SELECT COUNT(*) FROM public.sm_unified_ads_metrics WHERE platform = 'google_ads';",
    "network_data": "SELECT network, COUNT(*) FROM public.sm_unified_ads_metrics WHERE platform = 'google_ads' GROUP BY network ORDER BY COUNT(*) DESC;",
    "performance_data": "SELECT platform, COUNT(*) FROM public.sm_campaign_performance GROUP BY platform;",
    "google_performance_data": "SELECT COUNT(*) FROM public.sm_campaign_performance WHERE platform = 'google_ads';",
    "sample_unified": "SELECT * FROM public.sm_unified_ads_metrics WHERE platform = 'google_ads' LIMIT 5;",
    "sample_performance": "SELECT * FROM public.sm_campaign_performance WHERE platform = 'google_ads' LIMIT 5;",
    "campaign_overlap": """
        WITH fact_campaigns AS (
            SELECT DISTINCT campaign_id::VARCHAR AS id FROM public.sm_fact_google_ads
        ),
        mappings AS (
            SELECT external_campaign_id AS id FROM public.sm_campaign_name_mapping 
            WHERE source_system = 'Google Ads' AND is_active = TRUE
        )
        SELECT 
            (SELECT COUNT(*) FROM fact_campaigns) AS fact_count,
            (SELECT COUNT(*) FROM mappings) AS mapping_count,
            (SELECT COUNT(*) FROM fact_campaigns fc JOIN mappings m ON fc.id = m.id) AS overlap_count;
    """
}

def get_db_conn():
    """
    Get a connection to the Railway PostgreSQL database using hardcoded credentials
    """
    logger.info(f"Connecting to Railway PostgreSQL database at {DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    try:
        # Connection string format
        conn_string = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
        conn = psycopg2.connect(conn_string)
        logger.info("Connected to database successfully")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        sys.exit(1)

def execute_query(conn, query, description=None, return_results=True, quiet=False):
    """Execute a SQL query and optionally return results"""
    if description and not quiet:
        logger.info(f"Executing: {description}")
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor if return_results else None) as cursor:
            cursor.execute(query)
            if return_results:
                results = cursor.fetchall()
                if not quiet:
                    if results:
                        logger.info(f"Results: {json.dumps(results, default=str)[:500]}" + 
                                    ("..." if len(json.dumps(results, default=str)) > 500 else ""))
                    else:
                        logger.info("No results returned")
                return results
            else:
                if not quiet:
                    logger.info("Query executed successfully")
                return None
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return None

def run_diagnostics(conn):
    """Run diagnostic queries to check database state"""
    logger.info("Running diagnostics...")
    results = {}
    
    for name, query in DIAGNOSTIC_QUERIES.items():
        results[name] = execute_query(conn, query, f"Running {name} diagnostic")
    
    # Save results to file for reference
    output_file = f"railway_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Diagnostic results saved to {output_file}")
    return results

def recreate_views(conn):
    """Recreate the database views"""
    logger.info("Recreating database views...")
    
    # First drop the views
    execute_query(
        conn, 
        "DROP VIEW IF EXISTS public.sm_campaign_performance; DROP VIEW IF EXISTS public.sm_unified_ads_metrics;",
        "Dropping existing views",
        return_results=False
    )
    
    # Create the unified view
    execute_query(
        conn, 
        UNIFIED_VIEW_SQL,
        "Creating unified metrics view",
        return_results=False
    )
    
    # Create the performance view
    execute_query(
        conn, 
        PERFORMANCE_VIEW_SQL,
        "Creating campaign performance view",
        return_results=False
    )
    
    # Verify views were created
    views = execute_query(
        conn,
        "SELECT table_name FROM information_schema.views WHERE table_schema = 'public' AND table_name IN ('sm_unified_ads_metrics', 'sm_campaign_performance');",
        "Verifying views were created"
    )
    
    if not views or len(views) < 2:
        logger.warning("Views may not have been created successfully")
    else:
        logger.info("Views created successfully")

def check_view_data(conn):
    """Check data in the views"""
    logger.info("Checking view data...")
    
    # Check data in the views
    unified_count = execute_query(
        conn,
        "SELECT COUNT(*) FROM public.sm_unified_ads_metrics WHERE platform = 'google_ads';",
        "Checking Google Ads data in unified metrics view"
    )
    
    performance_count = execute_query(
        conn,
        "SELECT COUNT(*) FROM public.sm_campaign_performance WHERE platform = 'google_ads';",
        "Checking Google Ads data in campaign performance view"
    )
    
    # Display some sample data
    sample_unified = execute_query(
        conn,
        "SELECT * FROM public.sm_unified_ads_metrics WHERE platform = 'google_ads' LIMIT 5;",
        "Sample data from unified metrics view"
    )
    
    sample_performance = execute_query(
        conn,
        "SELECT * FROM public.sm_campaign_performance WHERE platform = 'google_ads' LIMIT 5;",
        "Sample data from campaign performance view"
    )

def main():
    """Main function to fix Railway database views"""
    logger.info("Starting Railway database view fix script...")
    
    try:
        # Connect to the database
        conn = get_db_conn()
        conn.autocommit = True
        
        # Run initial diagnostics
        logger.info("Running initial diagnostics...")
        initial_diagnostics = run_diagnostics(conn)
        
        # Recreate the views
        recreate_views(conn)
        
        # Check view data
        check_view_data(conn)
        
        # Run final diagnostics
        logger.info("Running final diagnostics...")
        final_diagnostics = run_diagnostics(conn)
        
        # Display summary
        logger.info("=== SUMMARY ===")
        
        # Before fix
        before_google_ads = 0
        if 'google_ads_count' in initial_diagnostics and initial_diagnostics['google_ads_count']:
            before_google_ads = initial_diagnostics['google_ads_count'][0].get('count', 0)
            
        before_mappings = 0
        if 'mappings' in initial_diagnostics and initial_diagnostics['mappings']:
            before_mappings = initial_diagnostics['mappings'][0].get('count', 0)
        
        # After fix
        after_unified = 0
        if 'google_unified_data' in final_diagnostics and final_diagnostics['google_unified_data']:
            after_unified = final_diagnostics['google_unified_data'][0].get('count', 0)
            
        after_performance = 0
        if 'google_performance_data' in final_diagnostics and final_diagnostics['google_performance_data']:
            after_performance = final_diagnostics['google_performance_data'][0].get('count', 0)
        
        logger.info(f"Google Ads records: {before_google_ads}")
        logger.info(f"Google Ads mappings: {before_mappings}")
        logger.info(f"After fix - Unified metrics view Google Ads records: {after_unified}")
        logger.info(f"After fix - Campaign performance view Google Ads records: {after_performance}")
        
        # Overlap info
        if 'campaign_overlap' in final_diagnostics and final_diagnostics['campaign_overlap']:
            overlap_data = final_diagnostics['campaign_overlap'][0]
            fact_count = overlap_data.get('fact_count', 0)
            mapping_count = overlap_data.get('mapping_count', 0)
            overlap_count = overlap_data.get('overlap_count', 0)
            
            logger.info(f"Campaign ID overlap analysis:")
            logger.info(f"  - Unique Google Ads campaign IDs: {fact_count}")
            logger.info(f"  - Active campaign mappings: {mapping_count}")
            logger.info(f"  - Overlap (campaigns with mappings): {overlap_count}")
            
            if fact_count > 0:
                coverage_pct = (overlap_count / fact_count) * 100
                logger.info(f"  - Mapping coverage: {coverage_pct:.2f}%")
        
        logger.info("Script execution complete. Check the diagnostic files for details.")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
