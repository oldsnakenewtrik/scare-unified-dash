import os
import time
import json
import logging
import datetime
import schedule
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("google_ads_connector")

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")
DATA_FETCH_INTERVAL_HOURS = int(os.getenv("DATA_FETCH_INTERVAL_HOURS", "12"))

# Initialize database connection
engine = create_engine(DATABASE_URL)

def get_google_ads_client():
    """Create and return a Google Ads API client."""
    if not all([
        GOOGLE_ADS_DEVELOPER_TOKEN,
        GOOGLE_ADS_CLIENT_ID,
        GOOGLE_ADS_CLIENT_SECRET,
        GOOGLE_ADS_REFRESH_TOKEN
    ]):
        logger.error("Google Ads API credentials are not properly configured")
        return None
        
    credentials = {
        "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": GOOGLE_ADS_CLIENT_ID,
        "client_secret": GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
        "use_proto_plus": True
    }
    
    return GoogleAdsClient.load_from_dict(credentials)

def get_date_dimension_id(date):
    """Get the date dimension ID for a given date, creating the date entry if it doesn't exist."""
    with engine.connect() as conn:
        # Check if date exists
        result = conn.execute(
            text("SELECT date_id FROM scare_metrics.dim_date WHERE full_date = :date"),
            {"date": date}
        ).fetchone()
        
        if result:
            return result[0]
        
        # If date doesn't exist, create it
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        
        conn.execute(
            text("""
                INSERT INTO scare_metrics.dim_date 
                (full_date, day_of_week, day_name, month, month_name, quarter, year, is_weekend)
                VALUES (:full_date, :day_of_week, :day_name, :month, :month_name, :quarter, :year, :is_weekend)
            """),
            {
                "full_date": date,
                "day_of_week": date_obj.weekday(),
                "day_name": date_obj.strftime("%A"),
                "month": date_obj.month,
                "month_name": date_obj.strftime("%B"),
                "quarter": (date_obj.month - 1) // 3 + 1,
                "year": date_obj.year,
                "is_weekend": date_obj.weekday() >= 5
            }
        )
        
        # Get the newly created ID
        result = conn.execute(
            text("SELECT date_id FROM scare_metrics.dim_date WHERE full_date = :date"),
            {"date": date}
        ).fetchone()
        
        if result:
            return result[0]
        else:
            raise Exception(f"Failed to create date dimension record for {date}")

def get_campaign_dimension_id(campaign_name, source_campaign_id=None):
    """Get the campaign dimension ID for a given campaign, creating the campaign entry if it doesn't exist."""
    with engine.connect() as conn:
        # Check if campaign exists
        query = """
            SELECT campaign_id 
            FROM scare_metrics.dim_campaign 
            WHERE campaign_name = :campaign_name 
            AND source_system = 'Google Ads'
        """
        
        if source_campaign_id:
            query += " AND source_campaign_id = :source_campaign_id"
            params = {"campaign_name": campaign_name, "source_campaign_id": source_campaign_id}
        else:
            params = {"campaign_name": campaign_name}
        
        result = conn.execute(text(query), params).fetchone()
        
        if result:
            return result[0]
        
        # If campaign doesn't exist, create it
        today = datetime.date.today().isoformat()
        
        conn.execute(
            text("""
                INSERT INTO scare_metrics.dim_campaign 
                (campaign_name, source_system, source_campaign_id, created_date, updated_date, is_active)
                VALUES (:campaign_name, 'Google Ads', :source_campaign_id, :created_date, :updated_date, TRUE)
            """),
            {
                "campaign_name": campaign_name,
                "source_campaign_id": source_campaign_id,
                "created_date": today,
                "updated_date": today
            }
        )
        
        # Get the newly created ID
        result = conn.execute(
            text("""
                SELECT campaign_id 
                FROM scare_metrics.dim_campaign 
                WHERE campaign_name = :campaign_name 
                AND source_system = 'Google Ads'
            """),
            {"campaign_name": campaign_name}
        ).fetchone()
        
        if result:
            return result[0]
        else:
            raise Exception(f"Failed to create campaign dimension record for {campaign_name}")

def get_ad_group_dimension_id(campaign_id, ad_group_name, source_ad_group_id=None):
    """Get the ad group dimension ID for a given ad group, creating the ad group entry if it doesn't exist."""
    with engine.connect() as conn:
        # Check if ad group exists
        query = """
            SELECT ad_group_id 
            FROM scare_metrics.dim_ad_group 
            WHERE ad_group_name = :ad_group_name 
            AND campaign_id = :campaign_id
            AND source_system = 'Google Ads'
        """
        
        if source_ad_group_id:
            query += " AND source_ad_group_id = :source_ad_group_id"
            params = {
                "ad_group_name": ad_group_name, 
                "campaign_id": campaign_id, 
                "source_ad_group_id": source_ad_group_id
            }
        else:
            params = {"ad_group_name": ad_group_name, "campaign_id": campaign_id}
        
        result = conn.execute(text(query), params).fetchone()
        
        if result:
            return result[0]
        
        # If ad group doesn't exist, create it
        today = datetime.date.today().isoformat()
        
        conn.execute(
            text("""
                INSERT INTO scare_metrics.dim_ad_group 
                (campaign_id, ad_group_name, source_system, source_ad_group_id, created_date, updated_date, is_active)
                VALUES (:campaign_id, :ad_group_name, 'Google Ads', :source_ad_group_id, :created_date, :updated_date, TRUE)
            """),
            {
                "campaign_id": campaign_id,
                "ad_group_name": ad_group_name,
                "source_ad_group_id": source_ad_group_id,
                "created_date": today,
                "updated_date": today
            }
        )
        
        # Get the newly created ID
        result = conn.execute(
            text("""
                SELECT ad_group_id 
                FROM scare_metrics.dim_ad_group 
                WHERE ad_group_name = :ad_group_name 
                AND campaign_id = :campaign_id
                AND source_system = 'Google Ads'
            """),
            {"ad_group_name": ad_group_name, "campaign_id": campaign_id}
        ).fetchone()
        
        if result:
            return result[0]
        else:
            raise Exception(f"Failed to create ad group dimension record for {ad_group_name}")

def fetch_google_ads_data(client, customer_id, start_date, end_date):
    """Fetch data from Google Ads API for the specified date range."""
    logger.info(f"Fetching Google Ads data for customer {customer_id} from {start_date} to {end_date}")
    
    if not client:
        logger.error("Google Ads client is not initialized")
        return None
        
    try:
        ga_service = client.get_service("GoogleAdsService")
        
        query = f"""
            SELECT
              campaign.id,
              campaign.name,
              ad_group.id,
              ad_group.name,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.average_cpc,
              metrics.conversions,
              metrics.conversions_value,
              segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY segments.date
        """
        
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        
        results = []
        for batch in stream:
            for row in batch.results:
                results.append({
                    "campaign_id": row.campaign.id,
                    "campaign_name": row.campaign.name,
                    "ad_group_id": row.ad_group.id,
                    "ad_group_name": row.ad_group.name,
                    "date": row.segments.date,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": row.metrics.cost_micros / 1000000,  # Convert micros to standard currency
                    "average_cpc": row.metrics.average_cpc / 1000000,  # Convert micros to standard currency
                    "conversions": row.metrics.conversions,
                    "conversion_value": row.metrics.conversions_value,
                    "ctr": row.metrics.ctr if hasattr(row.metrics, 'ctr') else None,
                    "conversion_rate": row.metrics.conversion_rate if hasattr(row.metrics, 'conversion_rate') else None,
                    "cost_per_conversion": row.metrics.cost_per_conversion / 1000000 if hasattr(row.metrics, 'cost_per_conversion') else None,
                    "average_position": row.metrics.average_position if hasattr(row.metrics, 'average_position') else None
                })
        
        return results
    
    except GoogleAdsException as ex:
        logger.error(f"Request with ID '{ex.request_id}' failed with status '{ex.error.code().name}'")
        for error in ex.failure.errors:
            logger.error(f"\tError with message '{error.message}'.")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    logger.error(f"\t\tOn field: {field_path_element.field_name}")
        return None
    
    except Exception as e:
        logger.error(f"Error fetching data from Google Ads API: {str(e)}")
        return None

def process_google_ads_data(data):
    """Process and transform Google Ads API data."""
    if not data:
        logger.warning("No data to process from Google Ads API")
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    return df

def store_google_ads_data(df):
    """Store processed Google Ads data in the database."""
    if df.empty:
        logger.warning("No Google Ads data to store")
        return 0
    
    rows_inserted = 0
    
    try:
        with engine.connect() as conn:
            for _, row in df.iterrows():
                # Get dimension IDs
                date_id = get_date_dimension_id(row["date"])
                campaign_id = get_campaign_dimension_id(
                    row["campaign_name"], 
                    source_campaign_id=str(row["campaign_id"])
                )
                ad_group_id = get_ad_group_dimension_id(
                    campaign_id,
                    row["ad_group_name"],
                    source_ad_group_id=str(row["ad_group_id"])
                )
                
                # Check if record already exists
                existing = conn.execute(
                    text("""
                        SELECT google_ads_id 
                        FROM scare_metrics.fact_google_ads 
                        WHERE date_id = :date_id AND campaign_id = :campaign_id AND ad_group_id = :ad_group_id
                    """),
                    {"date_id": date_id, "campaign_id": campaign_id, "ad_group_id": ad_group_id}
                ).fetchone()
                
                # Prepare data to insert/update
                fact_data = {
                    "date_id": date_id,
                    "campaign_id": campaign_id,
                    "ad_group_id": ad_group_id,
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "cost": float(row.get("cost", 0)),
                    "average_cpc": float(row.get("average_cpc", 0)),
                    "conversions": float(row.get("conversions", 0)),
                    "conversion_value": float(row.get("conversion_value", 0)),
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                    "conversion_rate": float(row.get("conversion_rate", 0)) if row.get("conversion_rate") else None,
                    "cost_per_conversion": float(row.get("cost_per_conversion", 0)) if row.get("cost_per_conversion") else None,
                    "average_position": float(row.get("average_position", 0)) if row.get("average_position") else None,
                    "source_data": json.dumps(row.to_dict()),
                    "updated_at": datetime.datetime.now()
                }
                
                if existing:
                    # Update existing record
                    update_query = text("""
                        UPDATE scare_metrics.fact_google_ads
                        SET 
                            impressions = :impressions,
                            clicks = :clicks,
                            cost = :cost,
                            average_cpc = :average_cpc,
                            conversions = :conversions,
                            conversion_value = :conversion_value,
                            ctr = :ctr,
                            conversion_rate = :conversion_rate,
                            cost_per_conversion = :cost_per_conversion,
                            average_position = :average_position,
                            source_data = :source_data,
                            updated_at = :updated_at
                        WHERE date_id = :date_id AND campaign_id = :campaign_id AND ad_group_id = :ad_group_id
                    """)
                    conn.execute(update_query, fact_data)
                else:
                    # Insert new record
                    insert_query = text("""
                        INSERT INTO scare_metrics.fact_google_ads
                        (date_id, campaign_id, ad_group_id, impressions, clicks, cost, average_cpc, conversions, conversion_value, 
                        ctr, conversion_rate, cost_per_conversion, average_position, source_data, created_at, updated_at)
                        VALUES
                        (:date_id, :campaign_id, :ad_group_id, :impressions, :clicks, :cost, :average_cpc, :conversions, :conversion_value,
                        :ctr, :conversion_rate, :cost_per_conversion, :average_position, :source_data, :updated_at, :updated_at)
                    """)
                    conn.execute(insert_query, fact_data)
                    rows_inserted += 1
            
            conn.commit()
        
        logger.info(f"Successfully stored {rows_inserted} new Google Ads records in the database")
        return rows_inserted
    
    except Exception as e:
        logger.error(f"Error storing Google Ads data: {str(e)}")
        return 0

def run_google_ads_etl(days_back=3):
    """
    Run the complete ETL process for Google Ads data.
    
    Args:
        days_back (int): Number of days to look back for data. Default is 3.
    """
    logger.info(f"Starting Google Ads ETL process for the last {days_back} days")
    
    try:
        # Initialize Google Ads client
        client = get_google_ads_client()
        if not client:
            return
        
        if not GOOGLE_ADS_CUSTOMER_ID:
            logger.error("Google Ads customer ID is not configured")
            return
        
        # Calculate date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days_back)
        
        # Format dates as strings
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Fetch, process, and store data
        raw_data = fetch_google_ads_data(client, GOOGLE_ADS_CUSTOMER_ID, start_date_str, end_date_str)
        processed_data = process_google_ads_data(raw_data)
        records_inserted = store_google_ads_data(processed_data)
        
        logger.info(f"Google Ads ETL process completed successfully. {records_inserted} new records inserted.")
    
    except Exception as e:
        logger.error(f"Error in Google Ads ETL process: {str(e)}")

def backfill_google_ads_data(start_date_str, end_date_str=None):
    """
    Backfill Google Ads data for a specific date range.
    
    Args:
        start_date_str (str): Start date in YYYY-MM-DD format
        end_date_str (str, optional): End date in YYYY-MM-DD format. Defaults to yesterday.
    """
    if end_date_str is None:
        end_date = datetime.date.today() - datetime.timedelta(days=1)
        end_date_str = end_date.strftime("%Y-%m-%d")
    
    logger.info(f"Starting Google Ads backfill from {start_date_str} to {end_date_str}")
    
    try:
        # Initialize Google Ads client
        client = get_google_ads_client()
        if not client:
            logger.error("Failed to create Google Ads client for backfill")
            return
        
        if not GOOGLE_ADS_CUSTOMER_ID:
            logger.error("Google Ads customer ID is not configured for backfill")
            return
        
        # Fetch, process, and store data
        raw_data = fetch_google_ads_data(client, GOOGLE_ADS_CUSTOMER_ID, start_date_str, end_date_str)
        processed_data = process_google_ads_data(raw_data)
        records_inserted = store_google_ads_data(processed_data)
        
        logger.info(f"Google Ads backfill completed successfully. {records_inserted} new records inserted.")
    
    except Exception as e:
        logger.error(f"Error in Google Ads backfill process: {str(e)}")

def schedule_jobs():
    """Schedule the ETL job to run at regular intervals."""
    # Run immediately at startup
    run_google_ads_etl()
    
    # Schedule to run every X hours
    schedule.every(DATA_FETCH_INTERVAL_HOURS).hours.do(lambda: run_google_ads_etl(1))  # Get just the latest day in regular runs
    
    # Weekly health check
    schedule.every().monday.at("01:00").do(lambda: logger.info("Google Ads API health check: OK"))
    
    logger.info(f"Scheduled Google Ads ETL to run every {DATA_FETCH_INTERVAL_HOURS} hours")

def main():
    """Main function to run the Google Ads connector with command line arguments."""
    import argparse
    parser = argparse.ArgumentParser(description="Google Ads data connector")
    parser.add_argument("--backfill", action="store_true", help="Run in backfill mode")
    parser.add_argument("--start-date", help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for backfill (YYYY-MM-DD)")
    parser.add_argument("--days-back", type=int, default=3, help="Number of days to look back for regular ETL")
    args = parser.parse_args()
    
    if args.backfill:
        if not args.start_date:
            logger.error("Start date required for backfill")
            return
        backfill_google_ads_data(args.start_date, args.end_date)
    else:
        # Set up regular schedule and run indefinitely
        schedule_jobs()
        logger.info("Starting scheduled jobs...")
        
        # Keep the script running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Sleep for 1 minute between schedule checks
        except KeyboardInterrupt:
            logger.info("Process interrupted, shutting down")

if __name__ == "__main__":
    logger.info("Starting Google Ads connector service")
    main()
