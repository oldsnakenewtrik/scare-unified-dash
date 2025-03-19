import os
import sys
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sqlalchemy as sa
from token_refresh import get_access_token, refresh_token
import schedule
import time
import json
import yaml
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('google_ads_connector')

# Load environment variables
load_dotenv()

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
except ImportError:
    logger.error("Failed to import Google Ads API libraries. Make sure they are installed.")
    sys.exit(1)

# Google Ads API credentials
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN')
GOOGLE_ADS_CLIENT_ID = os.getenv('GOOGLE_ADS_CLIENT_ID')
GOOGLE_ADS_CLIENT_SECRET = os.getenv('GOOGLE_ADS_CLIENT_SECRET')
GOOGLE_ADS_REFRESH_TOKEN = os.getenv('GOOGLE_ADS_REFRESH_TOKEN')
GOOGLE_ADS_CUSTOMER_ID = os.getenv('GOOGLE_ADS_CUSTOMER_ID')
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://scare_user:scare_password@localhost:5432/scare_metrics")
DATA_FETCH_INTERVAL_HOURS = int(os.getenv("DATA_FETCH_INTERVAL_HOURS", "12"))

# Initialize database connection
engine = sa.create_engine(DATABASE_URL)

def get_google_ads_client():
    """Create and return a Google Ads API client."""
    try:
        # List of potential YAML file paths to try
        yaml_paths = [
            # Local development path
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            # Railway paths
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            # Railway repository root path
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]

        # Try to load from YAML first (preferred method)
        yaml_path = None
        for path in yaml_paths:
            if os.path.exists(path):
                yaml_path = path
                logger.info(f"Found google-ads.yaml at: {path}")
                break
    
        if yaml_path:
            # Load from YAML file
            logger.info("Creating Google Ads client from YAML file")
            client = GoogleAdsClient.load_from_storage(yaml_path)
            logger.info("Successfully created Google Ads client from YAML")
            return client
        else:
            # Fallback to environment variables
            logger.info("YAML file not found, loading from environment variables")
            # Check if we need to refresh the token first
            if not get_access_token():
                refresh_token()
            
            # Load credentials from dictionary - more reliable approach
            credentials = {
                "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
                "client_id": GOOGLE_ADS_CLIENT_ID,
                "client_secret": GOOGLE_ADS_CLIENT_SECRET,
                "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
                "use_proto_plus": True,
                "version": "v18"
            }
            
            # Create the client
            client = GoogleAdsClient.load_from_dict(credentials)
            logger.info("Successfully created Google Ads client from environment variables")
            return client
    except Exception as e:
        logger.error(f"Error creating Google Ads client: {str(e)}")
        return None

def get_campaign_dimension_id(campaign_name, source_campaign_id=None):
    """
    Get or create a campaign dimension ID.
    
    Args:
        campaign_name (str): Name of the campaign
        source_campaign_id (str, optional): Original campaign ID from the source system
        
    Returns:
        int: Campaign dimension ID
    """
    with engine.connect() as conn:
        # Check if campaign exists
        query = sa.text("""
            SELECT campaign_id FROM scare_metrics.dim_campaign 
            WHERE campaign_name = :name OR source_campaign_id = :source_id
        """)
        
        result = conn.execute(query, {"name": campaign_name, "source_id": source_campaign_id}).fetchone()
        
        if result:
            return result[0]
        
        # Insert new campaign
        query = sa.text("""
            INSERT INTO scare_metrics.dim_campaign 
            (campaign_name, source_campaign_id, source_system, created_at) 
            VALUES (:name, :source_id, 'Google Ads', :created_at)
            RETURNING campaign_id
        """)
        
        result = conn.execute(query, {
            "name": campaign_name, 
            "source_id": source_campaign_id, 
            "created_at": datetime.now()
        }).fetchone()
        
        return result[0]

def get_ad_group_dimension_id(ad_group_name, campaign_id, source_ad_group_id=None):
    """
    Get or create an ad group dimension ID.
    
    Args:
        ad_group_name (str): Name of the ad group
        campaign_id (int): Campaign dimension ID
        source_ad_group_id (str, optional): Original ad group ID from the source system
        
    Returns:
        int: Ad group dimension ID
    """
    with engine.connect() as conn:
        # Check if ad group exists
        query = sa.text("""
            SELECT ad_group_id FROM scare_metrics.dim_ad_group 
            WHERE (ad_group_name = :name OR source_ad_group_id = :source_id)
            AND campaign_id = :campaign_id
        """)
        
        result = conn.execute(query, {
            "name": ad_group_name, 
            "source_id": source_ad_group_id,
            "campaign_id": campaign_id
        }).fetchone()
        
        if result:
            return result[0]
        
        # Insert new ad group
        query = sa.text("""
            INSERT INTO scare_metrics.dim_ad_group 
            (ad_group_name, campaign_id, source_ad_group_id, source_system, created_at) 
            VALUES (:name, :campaign_id, :source_id, 'Google Ads', :created_at)
            RETURNING ad_group_id
        """)
        
        result = conn.execute(query, {
            "name": ad_group_name, 
            "campaign_id": campaign_id,
            "source_id": source_ad_group_id, 
            "created_at": datetime.now()
        }).fetchone()
        
        return result[0]

def get_date_dimension_id(date_str):
    """
    Get or create a date dimension ID.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        int: Date dimension ID
    """
    with engine.connect() as conn:
        try:
            # Parse date string to datetime object
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Extract date components
            year = date_obj.year
            month = date_obj.month
            day = date_obj.day
            
            # Check if date exists
            query = sa.text("""
                SELECT date_id FROM scare_metrics.dim_date 
                WHERE year = :year AND month = :month AND day = :day
            """)
            
            result = conn.execute(query, {"year": year, "month": month, "day": day}).fetchone()
            
            if result:
                return result[0]
            
            # Insert new date
            query = sa.text("""
                INSERT INTO scare_metrics.dim_date 
                (year, month, day, full_date) 
                VALUES (:year, :month, :day, :full_date)
                RETURNING date_id
            """)
            
            result = conn.execute(query, {
                "year": year, 
                "month": month, 
                "day": day, 
                "full_date": date_obj
            }).fetchone()
            
            return result[0]
        except Exception as e:
            logger.error(f"Error getting date dimension ID: {str(e)}")
            # Return a default ID if something goes wrong
            return 1  # You may want to adjust this to a different strategy

def check_google_ads_health():
    """Test if we can connect to the Google Ads API and fetch basic data."""
    logger.info("Testing Google Ads API connection...")
    
    try:
        # Try to create a client
        client = get_google_ads_client()
        if not client:
            logger.error("❌ Failed to create Google Ads client")
            return False
        
        logger.info("✅ Successfully created Google Ads client")
        
        # Test basic API query
        try:
            # Simple query to fetch account information
            ga_service = client.get_service("GoogleAdsService")
            query = """
                SELECT customer.id, customer.descriptive_name
                FROM customer
                LIMIT 1
            """
            
            # Use search instead of search_stream for compatibility
            response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)
            
            # Process the response
            result_count = 0
            for row in response:
                result_count += 1
                logger.info(f"✅ Successfully connected to Google Ads account: {row.customer.descriptive_name} (ID: {row.customer.id})")
            
            if result_count > 0:
                return True
            
            logger.info("✅ Connected to API but no account information found.")
            return True
            
        except GoogleAdsException as ex:
            logger.error(f"❌ Google Ads API error: {ex.error.code().name}")
            for error in ex.failure.errors:
                logger.error(f"  - Error message: {error.message}")
                if error.location:
                    for field_path_element in error.location.field_path_elements:
                        logger.error(f"    - On field: {field_path_element.field_name}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to connect to Google Ads API: {str(e)}")
        return False

def fetch_google_ads_data(start_date, end_date):
    """
    Fetch data from Google Ads API for the specified date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Fetching Google Ads data from {start_date} to {end_date}...")
    
    client = get_google_ads_client()
    if not client:
        logger.error("Failed to create Google Ads client. Aborting data fetch.")
        return []
    
    try:
        # Use the service in a way that's compatible with v14
        ga_service = client.get_service("GoogleAdsService")
        
        # Construct the query to fetch campaign metrics
        query = f"""
            SELECT
              campaign.id,
              campaign.name,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.ctr,
              metrics.average_cpc,
              metrics.conversions,
              metrics.conversions_value,
              segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY segments.date
        """
        
        logger.info(f"Executing Google Ads query...")
        
        # Use search instead of search_stream for better compatibility
        search_request = client.get_type("SearchGoogleAdsRequest")
        search_request.customer_id = GOOGLE_ADS_CUSTOMER_ID
        search_request.query = query
        
        # Execute the request
        response = ga_service.search(request=search_request)
        
        # Process the results
        campaign_data = []
        
        for row in response.results:
            # Extract data from the row and handle fields carefully to avoid None errors
            data = {
                "campaign_id": str(row.campaign.id),
                "campaign_name": row.campaign.name,
                "impressions": float(row.metrics.impressions) if row.metrics.impressions else 0,
                "clicks": float(row.metrics.clicks) if row.metrics.clicks else 0,
                "cost": float(row.metrics.cost_micros) / 1_000_000 if row.metrics.cost_micros else 0,  # Convert from micros to dollars
                "ctr": float(row.metrics.ctr) if row.metrics.ctr else 0,
                "average_cpc": float(row.metrics.average_cpc) / 1_000_000 if row.metrics.average_cpc else 0,
                "conversions": float(row.metrics.conversions) if row.metrics.conversions else 0,
                "conversions_value": float(row.metrics.conversions_value) if row.metrics.conversions_value else 0,
                "date": row.segments.date
            }
            
            campaign_data.append(data)
                
        logger.info(f"Successfully fetched {len(campaign_data)} rows of campaign data")
        return campaign_data
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex.error.code().name}")
        for error in ex.failure.errors:
            logger.error(f"  - Error message: {error.message}")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    logger.error(f"    - On field: {field_path_element.field_name}")
        return []
    except Exception as e:
        logger.error(f"Error fetching Google Ads data: {str(e)}")
        return []

def process_google_ads_data(data):
    """Process and transform Google Ads API data."""
    if not data:
        logger.warning("No data to process from Google Ads API")
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    return df

def store_google_ads_data(data):
    """
    Store the processed Google Ads data in the database.
    
    Args:
        data (List[Dict]): List of processed campaign data dictionaries
        
    Returns:
        int: Number of records inserted/updated
    """
    if not data:
        logger.warning("No data to store in database")
        return 0
        
    try:
        logger.info(f"Storing {len(data)} records in database")
        
        # Initialize connection
        engine = sa.create_engine(DATABASE_URL)
        
        records_affected = 0
        
        with engine.begin() as conn:
            # Process each record
            for item in data:
                # Get dimension IDs
                campaign_id = get_campaign_dimension_id(
                    item['campaign_name'],
                    str(item['campaign_id'])
                )
                
                date_id = get_date_dimension_id(item['date'])
                
                # Calculate CTR (Click-Through Rate) if not provided
                if 'ctr' not in item and item['impressions'] > 0:
                    ctr = (item['clicks'] / item['impressions']) * 100
                else:
                    ctr = item.get('ctr', 0)
                
                # Get average CPC from the item or calculate it
                if 'average_cpc' not in item and item['clicks'] > 0:
                    avg_cpc = item['cost'] / item['clicks']
                else:
                    avg_cpc = item.get('average_cpc', 0)
                
                # Check if record already exists
                check_query = sa.text("""
                    SELECT id
                    FROM scare_metrics.fact_google_ads
                    WHERE campaign_id = :campaign_id
                    AND date_id = :date_id
                """)
                
                existing = conn.execute(
                    check_query,
                    {"campaign_id": campaign_id, "date_id": date_id}
                ).fetchone()
                
                if existing:
                    # Update existing record
                    update_query = sa.text("""
                        UPDATE scare_metrics.fact_google_ads
                        SET 
                            impressions = :impressions,
                            clicks = :clicks,
                            cost = :cost,
                            average_cpc = :average_cpc,
                            ctr = :ctr,
                            conversions = :conversions,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE campaign_id = :campaign_id
                        AND date_id = :date_id
                    """)
                    
                    conn.execute(
                        update_query,
                        {
                            "campaign_id": campaign_id,
                            "date_id": date_id,
                            "impressions": item['impressions'],
                            "clicks": item['clicks'],
                            "cost": item['cost'],
                            "average_cpc": avg_cpc,
                            "ctr": ctr,
                            "conversions": item.get('conversions', 0)
                        }
                    )
                else:
                    # Insert new record
                    insert_query = sa.text("""
                        INSERT INTO scare_metrics.fact_google_ads (
                            campaign_id,
                            date_id,
                            impressions,
                            clicks,
                            cost,
                            average_cpc,
                            ctr,
                            conversions,
                            created_at,
                            updated_at
                        ) VALUES (
                            :campaign_id,
                            :date_id,
                            :impressions,
                            :clicks,
                            :cost,
                            :average_cpc,
                            :ctr,
                            :conversions,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                    """)
                    
                    conn.execute(
                        insert_query,
                        {
                            "campaign_id": campaign_id,
                            "date_id": date_id,
                            "impressions": item['impressions'],
                            "clicks": item['clicks'],
                            "cost": item['cost'],
                            "average_cpc": avg_cpc,
                            "ctr": ctr,
                            "conversions": item.get('conversions', 0)
                        }
                    )
                
                records_affected += 1
            
        logger.info(f"Successfully stored {records_affected} records in database")
        return records_affected
        
    except Exception as e:
        logger.error(f"Error storing Google Ads data: {str(e)}")
        raise

def run_google_ads_etl(days_back=3):
    """
    Run the full ETL process for Google Ads data.
    
    Args:
        days_back (int): Number of days to go back for data fetching
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Starting Google Ads ETL process, fetching data for the last {days_back} days")
        
        # Get date range
        end_date = datetime.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Fetch data
        data = fetch_google_ads_data(start_date_str, end_date_str)
        
        if not data:
            logger.warning("No data fetched from Google Ads API")
            return False
        
        # Save to JSON for backup
        output_file = f"google_ads_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Raw data saved to {output_file}")
        
        try:
            # Process and store data
            processed_data = process_google_ads_data(data)
            records_affected = store_google_ads_data(processed_data)
            
            logger.info(f"ETL process completed successfully. {records_affected} records affected.")
            return True
        except Exception as db_error:
            logger.error(f"Database operation failed: {str(db_error)}. Data saved to {output_file} for later import.")
            return False
        
    except Exception as e:
        logger.error(f"Error running Google Ads ETL process: {str(e)}")
        return False

def backfill_google_ads_data(start_date_str, end_date_str=None):
    """
    Backfill Google Ads data for a specified date range.
    
    Args:
        start_date_str (str): Start date in YYYY-MM-DD format
        end_date_str (str, optional): End date in YYYY-MM-DD format. Defaults to yesterday.
    """
    if end_date_str is None:
        end_date = datetime.today() - timedelta(days=1)
        end_date_str = end_date.strftime("%Y-%m-%d")
    
    logger.info(f"Starting Google Ads backfill from {start_date_str} to {end_date_str}")
    
    # Check if we can connect to the API
    client = get_google_ads_client()
    if not client:
        logger.error("Failed to create Google Ads client. Aborting backfill process.")
        return
        
    # Fetch, process, and store data
    raw_data = fetch_google_ads_data(start_date_str, end_date_str)
    records_inserted = store_google_ads_data(raw_data)
    
    logger.info(f"Google Ads backfill complete: {records_inserted} records processed from {start_date_str} to {end_date_str}")

def setup_scheduled_tasks():
    """Set up scheduled tasks for Google Ads data fetching."""
    # Schedule the ETL process to run daily
    schedule.every().day.at("03:00").do(run_google_ads_etl, days_back=3)
    
    logger.info("Scheduled Google Ads ETL tasks set up")
    
    # Run the scheduler in a loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def main():
    """Main entry point for the Google Ads connector."""
    logger.info("Starting Google Ads connector service")
    
    parser = argparse.ArgumentParser(description="Google Ads Connector Service")
    parser.add_argument("--check-health", action="store_true", help="Check Google Ads API connection")
    parser.add_argument("--backfill", action="store_true", help="Backfill Google Ads data")
    parser.add_argument("--start-date", help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for backfill (YYYY-MM-DD)")
    parser.add_argument("--days-back", type=int, default=3, help="Days back to fetch data for regular ETL")
    parser.add_argument("--schedule", action="store_true", help="Run scheduled ETL tasks")
    
    args = parser.parse_args()
    
    if args.check_health:
        logger.info("Running health check for Google Ads API connection")
        check_google_ads_health()
        return
            
    if args.backfill:
        if not args.start_date:
            logger.error("Start date is required for backfill")
            return
            
        backfill_google_ads_data(args.start_date, args.end_date)
        return
        
    if args.schedule:
        logger.info("Starting scheduled ETL tasks")
        setup_scheduled_tasks()
        return
        
    # Default behavior: run ETL once
    run_google_ads_etl(days_back=args.days_back)

if __name__ == "__main__":
    main()
