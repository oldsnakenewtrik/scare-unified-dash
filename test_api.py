import requests
import json
import datetime
import logging
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Base URL for the Railway-deployed app
    base_url = "https://scare-unified-dash-production.up.railway.app"
    
    # API endpoints to test
    endpoints = [
        # Health check endpoint
        "/api/health",
        
        # Campaign metrics endpoint - current month
        f"/api/campaign-metrics?start_date={datetime.date.today().replace(day=1).isoformat()}&end_date={datetime.date.today().isoformat()}",
        
        # Campaign metrics endpoint - previous month
        f"/api/campaign-metrics?start_date={(datetime.date.today().replace(day=1) - datetime.timedelta(days=30)).isoformat()}&end_date={(datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).isoformat()}",
        
        # Campaign metrics endpoint - all time (last 365 days)
        f"/api/campaign-metrics?start_date={(datetime.date.today() - datetime.timedelta(days=365)).isoformat()}&end_date={datetime.date.today().isoformat()}",
        
        # Campaign metrics endpoint - Google Ads only
        f"/api/campaign-metrics?start_date={(datetime.date.today() - datetime.timedelta(days=365)).isoformat()}&end_date={datetime.date.today().isoformat()}&platform=google_ads",
    ]
    
    # Test each endpoint
    for endpoint in endpoints:
        url = urljoin(base_url, endpoint)
        logger.info(f"Testing endpoint: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        logger.info(f"Received {len(data)} items")
                        if len(data) > 0:
                            # Print first item as sample
                            logger.info(f"Sample item: {json.dumps(data[0], indent=2)}")
                        else:
                            logger.warning("Received empty array - no data returned")
                    else:
                        logger.info(f"Response: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    logger.error("Could not parse JSON response")
                    logger.info(f"Raw response: {response.text[:200]}...")
            else:
                logger.error(f"Request failed with status code {response.status_code}")
                logger.info(f"Response: {response.text[:200]}...")
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
    
    # Now let's test a local API request - run the same query through SQLAlchemy
    logger.info("\nTesting local database query:")
    try:
        import os
        import psycopg2
        from datetime import date, timedelta
        
        # Database connection
        db_url = "postgresql://postgres:HGnALEQyXYobjgWixRVpnfQBVXcfTXoF@nozomi.proxy.rlwy.net:11923/railway"
        conn = psycopg2.connect(db_url)
        
        # Query to get campaign metrics
        query = """
            SELECT 
                platform,
                network,
                campaign_id,
                campaign_name,
                original_campaign_name,
                campaign_category,
                campaign_type,
                SUM(impressions) as impressions,
                SUM(clicks) as clicks,
                SUM(cost) as cost,
                SUM(conversions) as conversions,
                AVG(ctr) as ctr,
                AVG(conversion_rate) as conversion_rate,
                AVG(cost_per_conversion) as cost_per_conversion
            FROM public.sm_campaign_performance
            WHERE date BETWEEN %s AND %s
            GROUP BY 
                platform, 
                network,
                campaign_id, 
                campaign_name, 
                original_campaign_name,
                campaign_category,
                campaign_type
            ORDER BY cost DESC
        """
        
        # Date range (last 365 days)
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()
        
        # Execute query
        with conn.cursor() as cursor:
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            
            if rows:
                logger.info(f"Direct query returned {len(rows)} rows")
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                
                # Convert first row to dictionary for readability
                if rows:
                    sample_row = dict(zip(columns, rows[0]))
                    logger.info(f"Sample row: {json.dumps(sample_row, default=str, indent=2)}")
            else:
                logger.warning("Direct query returned no data")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")

if __name__ == "__main__":
    main()
