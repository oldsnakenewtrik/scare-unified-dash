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
from sqlalchemy import text

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

# Create database engine
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
        return sa.create_engine(connection_string)
    elif railway_database_url:
        logger.info("Creating database engine with RAILWAY_DATABASE_URL environment variable")
        return sa.create_engine(railway_database_url)
    elif database_url:
        logger.info("Creating database engine with DATABASE_URL environment variable")
        return sa.create_engine(database_url)
    else:
        logger.error("No database connection information found in environment variables")
        # Print available environment variables for debugging
        logger.info("Available environment variables:")
        for key in os.environ:
            if "DATABASE" in key or "PG" in key or "SQL" in key:
                logger.info(f"  - {key}: {'*' * min(len(os.environ[key]), 5)}")
        return None

# Create engine
engine = get_db_engine()

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
                "version": "v14"
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
              metrics.conversions,
              segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY segments.date
        """
        
        logger.info(f"Executing query: {query}")
        
        # Determine the customer ID
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        customer_id = GOOGLE_ADS_CUSTOMER_ID  # Default to env variable
        
        # Try to load from YAML if available
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"Loading customer ID from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    yaml_customer_id = config.get('customer_id') or config.get('linked_customer_id') or config.get('login_customer_id')
                    if yaml_customer_id:
                        customer_id = yaml_customer_id
                        logger.info(f"Using customer ID from YAML: {customer_id}")
                        break
        
        # Ensure customer_id is a string
        customer_id = str(customer_id)
        logger.info(f"Using customer ID: {customer_id}")
        
        # Use search instead of search_stream for better compatibility
        response = ga_service.search(customer_id=customer_id, query=query)
        
        # Process the response into a list of dictionaries
        results = []
        row_count = 0
        
        for row in response:
            row_count += 1
            # Extract the data from the row
            campaign_id = row.campaign.id
            campaign_name = row.campaign.name
            impressions = row.metrics.impressions
            clicks = row.metrics.clicks
            cost_micros = row.metrics.cost_micros
            conversions = row.metrics.conversions
            date = row.segments.date
            
            # Create a dictionary for this row
            row_data = {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "impressions": impressions,
                "clicks": clicks,
                "cost_micros": cost_micros,
                "conversions": conversions,
                "date": date
            }
            
            results.append(row_data)
        
        logger.info(f"Successfully fetched {row_count} rows of Google Ads data")
        return results
        
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
        import traceback
        logger.error(traceback.format_exc())
        return []

def process_google_ads_data(raw_data):
    """
    Process raw data from Google Ads API into a format suitable for database storage.
    
    Args:
        raw_data (List[Dict]): Raw data from Google Ads API
        
    Returns:
        List[Dict]: Processed data ready for database insertion
    """
    logger.info(f"Processing {len(raw_data)} rows of Google Ads data")
    
    processed_data = []
    
    for row in raw_data:
        # Convert cost from micros (millionths of the account currency) to actual currency value
        cost_micros = row.get('cost_micros', 0)
        cost = float(cost_micros) / 1000000.0 if cost_micros else 0.0
        
        # Create a processed row
        processed_row = {
            'date': row.get('date'),
            'campaign_id': str(row.get('campaign_id')),  # Ensure campaign_id is a string
            'campaign_name': row.get('campaign_name'),
            'impressions': int(row.get('impressions', 0)),
            'clicks': int(row.get('clicks', 0)),
            'cost': cost,  # Converted from micros
            'conversions': float(row.get('conversions', 0)),
            'created_at': datetime.now()
        }
        
        processed_data.append(processed_row)
    
    logger.info(f"Processed {len(processed_data)} rows of Google Ads data")
    return processed_data

def store_google_ads_data(processed_data):
    """
    Store processed Google Ads data in the database.
    
    Args:
        processed_data (List[Dict]): Processed data ready for database insertion
        
    Returns:
        int: Number of records affected
    """
    if not processed_data:
        logger.warning("No data to store")
        return 0
    
    logger.info(f"Storing {len(processed_data)} records in the database...")
    
    try:
        # Get database engine
        if not engine:
            logger.error("No database engine available")
            return 0
        
        # Create a connection
        with engine.connect() as conn:
            # Check if the table exists, create it if not
            if not conn.dialect.has_table(conn, 'sm_fact_google_ads'):
                logger.info("Creating sm_fact_google_ads table")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS public.sm_fact_google_ads (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        campaign_id VARCHAR(255) NOT NULL,
                        campaign_name VARCHAR(255) NOT NULL,
                        impressions INT DEFAULT 0,
                        clicks INT DEFAULT 0,
                        cost DECIMAL(12,2) DEFAULT 0,
                        conversions DECIMAL(12,2) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT sm_fact_google_ads_date_campaign_id_key UNIQUE (date, campaign_id)
                    )
                """))
                logger.info("sm_fact_google_ads table created")
            
            # Begin a transaction
            trans = conn.begin()
            
            try:
                # Insert data
                records_affected = 0
                
                # Check if the table has the unique constraint
                constraint_query = text("""
                    SELECT COUNT(*) FROM pg_constraint 
                    WHERE conrelid = 'public.sm_fact_google_ads'::regclass 
                    AND contype = 'u'
                """)
                
                has_constraint = False
                try:
                    has_constraint = conn.execute(constraint_query).scalar() > 0
                except Exception as e:
                    logger.warning(f"Could not check for constraint: {str(e)}")
                
                # If no constraint exists, add one
                if not has_constraint:
                    logger.info("Adding unique constraint to sm_fact_google_ads table")
                    try:
                        conn.execute(text("""
                            ALTER TABLE public.sm_fact_google_ads 
                            ADD CONSTRAINT sm_fact_google_ads_date_campaign_id_key 
                            UNIQUE (date, campaign_id)
                        """))
                        logger.info("Added unique constraint")
                    except Exception as e:
                        logger.warning(f"Could not add constraint: {str(e)}")
                
                # Use a more robust insert approach that works with or without the constraint
                for row in processed_data:
                    try:
                        # First check if the record exists
                        check_query = text("""
                            SELECT id FROM public.sm_fact_google_ads
                            WHERE date = :date AND campaign_id = :campaign_id
                        """)
                        existing_id = conn.execute(check_query, {
                            'date': row['date'],
                            'campaign_id': row['campaign_id']
                        }).scalar()
                        
                        if existing_id:
                            # Update existing record
                            update_stmt = text("""
                                UPDATE public.sm_fact_google_ads
                                SET 
                                    campaign_name = :campaign_name,
                                    impressions = :impressions,
                                    clicks = :clicks,
                                    cost = :cost,
                                    conversions = :conversions,
                                    created_at = :created_at
                                WHERE id = :id
                            """)
                            result = conn.execute(update_stmt, {**row, 'id': existing_id})
                        else:
                            # Insert new record
                            insert_stmt = text("""
                                INSERT INTO public.sm_fact_google_ads 
                                (date, campaign_id, campaign_name, impressions, clicks, cost, conversions, created_at)
                                VALUES (:date, :campaign_id, :campaign_name, :impressions, :clicks, :cost, :conversions, :created_at)
                            """)
                            result = conn.execute(insert_stmt, row)
                        
                        records_affected += 1
                    except Exception as e:
                        logger.error(f"Error inserting/updating row: {str(e)}")
                        logger.error(f"Row data: {row}")
                
                # Commit the transaction
                trans.commit()
                logger.info(f"Successfully stored {records_affected} records")
                return records_affected
                
            except Exception as e:
                # Rollback the transaction on error
                trans.rollback()
                logger.error(f"Error storing Google Ads data: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return 0
                
    except Exception as e:
        logger.error(f"Error connecting to database for storing Google Ads data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def run_google_ads_etl(days=3):
    """
    Run the full ETL process for Google Ads data.
    
    Args:
        days (int): Number of days to go back for data fetching
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting Google Ads ETL process, fetching data for the last {days} days")
    
    try:
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Format dates as strings
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Fetch data from API
        raw_data = fetch_google_ads_data(start_date_str, end_date_str)
        
        if not raw_data:
            logger.warning("No data fetched from Google Ads API")
            return False
        
        # Process the data
        processed_data = process_google_ads_data(raw_data)
        
        # Store in database
        records_affected = store_google_ads_data(processed_data)
        
        if records_affected > 0:
            logger.info(f"Successfully completed Google Ads ETL process, affected {records_affected} records")
            return True
        else:
            logger.warning("No records affected in the database")
            return False
        
    except Exception as e:
        logger.error(f"Error running Google Ads ETL process: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def backfill_google_ads_data(start_date_str, end_date_str=None):
    """
    Backfill Google Ads data for a date range.
    
    Args:
        start_date_str (str): Start date in YYYY-MM-DD format
        end_date_str (str, optional): End date in YYYY-MM-DD format. Defaults to today.
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Starting Google Ads backfill process from {start_date_str} to {end_date_str or 'today'}")
        
        # Set end date to today if not provided
        if not end_date_str:
            end_date_str = datetime.now().strftime('%Y-%m-%d')
            
        # Fetch data from API
        raw_data = fetch_google_ads_data(start_date_str, end_date_str)
        
        if not raw_data:
            logger.warning(f"No data fetched from Google Ads API for date range {start_date_str} to {end_date_str}")
            return False
        
        # Process the data
        processed_data = process_google_ads_data(raw_data)
        
        # Store in database
        records_affected = store_google_ads_data(processed_data)
        
        if records_affected > 0:
            logger.info(f"Successfully completed Google Ads backfill, affected {records_affected} records")
            return True
        else:
            logger.warning("No records affected in the database during backfill")
            return False
        
    except Exception as e:
        logger.error(f"Error running Google Ads backfill: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def setup_scheduled_tasks():
    """Set up scheduled tasks for Google Ads data fetching."""
    import schedule
    import time
    import threading
    
    logger.info("Setting up scheduled tasks for Google Ads data fetching")
    
    # Function to run in a separate thread
    def run_scheduled_job():
        logger.info("Starting scheduled Google Ads ETL job")
        # Fetch data to JSON
        fetch_and_save(days_back=3)
        # Wait a bit to ensure file is saved
        time.sleep(5)
        # Import latest file to database
        import_latest_json()
    
    # Function to import the latest JSON file
    def import_latest_json():
        try:
            # Find the latest JSON file in the data directory
            import glob
            import os
            
            data_dir = os.path.join(os.getcwd(), "data")
            files = glob.glob(os.path.join(data_dir, "google_ads_data_*.json"))
            
            if not files:
                logger.warning("No JSON files found in data directory")
                return
            
            # Sort by modification time (newest first)
            latest_file = max(files, key=os.path.getmtime)
            logger.info(f"Found latest JSON file: {latest_file}")
            
            # Import to database
            from import_from_json import import_google_ads_data
            records = import_google_ads_data(latest_file)
            logger.info(f"Imported {records} records from {latest_file}")
            
        except Exception as e:
            logger.error(f"Error importing latest JSON file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Function to fetch data and save to JSON
    def fetch_and_save(days_back=3):
        try:
            from datetime import datetime, timedelta
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            from fetch_to_json import fetch_and_save as fetch_to_json_save
            filepath = fetch_to_json_save(start_date_str, end_date_str)
            
            if filepath:
                logger.info(f"Successfully fetched and saved Google Ads data to {filepath}")
            else:
                logger.warning("Failed to fetch and save Google Ads data")
                
        except Exception as e:
            logger.error(f"Error fetching and saving Google Ads data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def run_threaded(job_func):
        job_thread = threading.Thread(target=job_func)
        job_thread.start()
    
    # Schedule job to run every 4 hours
    schedule.every(4).hours.do(run_threaded, run_scheduled_job)
    
    # Also run once at startup
    run_threaded(run_scheduled_job)
    
    # Run the scheduler in a separate thread
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("Scheduled tasks set up successfully (running every 4 hours)")
    
    return scheduler_thread

def main():
    """Main entry point for the Google Ads connector."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Google Ads ETL Service')
    parser.add_argument('--run-once', action='store_true', help='Run ETL process once and exit')
    parser.add_argument('--days', type=int, default=30, help='Number of days of data to fetch (default: 30)')
    parser.add_argument('--interval', type=int, default=6, help='Hours between ETL runs (default: 6)')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database engine
    engine = get_db_engine()
    
    if not engine:
        logger.error("Failed to initialize database engine. Exiting.")
        sys.exit(1)
    
    # If run-once flag is set, run ETL process once and exit
    if args.run_once:
        logger.info("Running Google Ads ETL process once...")
        try:
            run_google_ads_etl(days=args.days)
            logger.info("ETL process completed successfully.")
        except Exception as e:
            logger.error(f"Error running ETL process: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(0)
    
    # Otherwise, run as a service with scheduled ETL runs
    logger.info(f"Starting Google Ads ETL service with {args.interval} hour interval")
    
    # Run ETL process immediately
    try:
        run_google_ads_etl(days=args.days)
        logger.info("Initial ETL process completed successfully.")
    except Exception as e:
        logger.error(f"Error running initial ETL process: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Schedule ETL process to run at regular intervals
    schedule.every(args.interval).hours.do(run_google_ads_etl, days=args.days)
    
    # Keep the script running and check for scheduled jobs
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Service stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error in scheduler loop: {str(e)}")
            time.sleep(300)  # Wait 5 minutes before retrying on error

if __name__ == "__main__":
    import sys
    sys.exit(main())
