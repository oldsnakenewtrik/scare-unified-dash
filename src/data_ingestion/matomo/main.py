#!/usr/bin/env python3
"""
Matomo Analytics API integration for SCARE Unified Dashboard
"""
import os
import time
import json
import logging
import datetime
import schedule
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("matomo_connector")

# Load environment variables
load_dotenv()

# Configuration
MATOMO_API_URL = os.getenv("MATOMO_API_URL", "https://sondercare.matomo.cloud/index.php")
MATOMO_SITE_ID = os.getenv("MATOMO_SITE_ID", "1")
MATOMO_AUTH_TOKEN = os.getenv("MATOMO_AUTH_TOKEN", "4e70e8b80438c7afe669fd41d2ef82bf")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")
DATA_FETCH_INTERVAL_HOURS = int(os.getenv("DATA_FETCH_INTERVAL_HOURS", "12"))

# Initialize database connection
engine = create_engine(DATABASE_URL)

def get_date_dimension_id(date):
    """
    Get the date dimension ID for a given date, creating the date entry if it doesn't exist.
    
    Args:
        date (str): Date in YYYY-MM-DD format
        
    Returns:
        int: Date dimension ID
    """
    with engine.connect() as connection:
        # Check if date already exists
        query = text("SELECT id FROM sm_dim_date WHERE date = :date")
        result = connection.execute(query, {"date": date}).fetchone()
        
        if result:
            return result[0]
        
        # Convert to datetime for additional fields
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.year
        month = date_obj.month
        day = date_obj.day
        day_of_week = date_obj.weekday()
        
        # Insert new date
        query = text("""
            INSERT INTO sm_dim_date (date, year, month, day, day_of_week)
            VALUES (:date, :year, :month, :day, :day_of_week)
            RETURNING id
        """)
        
        result = connection.execute(
            query,
            {
                "date": date,
                "year": year,
                "month": month,
                "day": day,
                "day_of_week": day_of_week
            }
        ).fetchone()
        
        return result[0]

def get_campaign_dimension_id(campaign_name, source_campaign_id=None):
    """
    Get the campaign dimension ID for a given campaign, creating the campaign entry if it doesn't exist.
    
    Args:
        campaign_name (str): Campaign name
        source_campaign_id (str, optional): ID of the campaign in the source system. Defaults to None.
        
    Returns:
        int: Campaign dimension ID
    """
    if not campaign_name:
        campaign_name = "Direct / None"
        
    with engine.connect() as connection:
        # Check if campaign already exists
        query = text("SELECT id FROM sm_dim_campaign WHERE campaign_name = :campaign_name")
        result = connection.execute(query, {"campaign_name": campaign_name}).fetchone()
        
        if result:
            return result[0]
        
        # Normalize source_campaign_id
        if not source_campaign_id:
            source_campaign_id = campaign_name
        
        # Insert new campaign
        query = text("""
            INSERT INTO sm_dim_campaign (campaign_name, source_campaign_id)
            VALUES (:campaign_name, :source_campaign_id)
            RETURNING id
        """)
        
        result = connection.execute(
            query,
            {
                "campaign_name": campaign_name,
                "source_campaign_id": source_campaign_id
            }
        ).fetchone()
        
        return result[0]

def fetch_matomo_data(start_date, end_date):
    """
    Fetch data from Matomo API for the specified date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        list: List of dictionaries containing Matomo data
    """
    logger.info(f"Fetching Matomo data from {start_date} to {end_date}")
    
    # Basic API parameters for visits summary
    visit_params = {
        'module': 'API',
        'method': 'VisitsSummary.get',
        'idSite': MATOMO_SITE_ID,
        'period': 'day',
        'date': f'{start_date},{end_date}',
        'format': 'JSON',
        'token_auth': MATOMO_AUTH_TOKEN
    }
    
    # Parameters for campaign data
    campaign_params = {
        'module': 'API',
        'method': 'Referrers.getCampaigns',
        'idSite': MATOMO_SITE_ID,
        'period': 'day',
        'date': f'{start_date},{end_date}',
        'format': 'JSON',
        'token_auth': MATOMO_AUTH_TOKEN,
        'filter_limit': 1000  # Ensure we get all campaigns
    }
    
    try:
        # First get daily metrics
        logger.info("Requesting VisitsSummary.get data")
        daily_metrics_url = f"{MATOMO_API_URL}"
        daily_response = requests.get(daily_metrics_url, params=visit_params, timeout=15)
        daily_response.raise_for_status()
        daily_data = daily_response.json()
        
        # Then get campaign data
        logger.info("Requesting Referrers.getCampaigns data")
        campaigns_url = f"{MATOMO_API_URL}"
        campaigns_response = requests.get(campaigns_url, params=campaign_params, timeout=15)
        campaigns_response.raise_for_status()
        campaigns_data = campaigns_response.json()
        
        # Process and merge both datasets
        result = []
        for date, daily_metrics in daily_data.items():
            # Skip any non-data entries
            if not isinstance(daily_metrics, dict):
                continue
                
            # Get campaign data for this date
            campaign_metrics = campaigns_data.get(date, {})
            
            if not campaign_metrics or not isinstance(campaign_metrics, list) or len(campaign_metrics) == 0:
                # If no campaign data, record site-wide metrics under "(not set)" campaign
                result.append({
                    "date": date,
                    "campaign_name": "(not set)",
                    "visits": daily_metrics.get("nb_visits", 0),
                    "unique_visitors": daily_metrics.get("nb_uniq_visitors", 0),
                    "page_views": daily_metrics.get("nb_pageviews", 0),
                    "bounce_rate": daily_metrics.get("bounce_rate", 0),
                    "avg_time_on_site": daily_metrics.get("avg_time_on_site", 0),
                    "revenue": 0,
                })
            else:
                # Record metrics per campaign
                for campaign in campaign_metrics:
                    result.append({
                        "date": date,
                        "campaign_name": campaign.get("label", "(not set)"),
                        "visits": campaign.get("nb_visits", 0),
                        "unique_visitors": campaign.get("nb_uniq_visitors", 0),
                        "page_views": campaign.get("nb_actions", 0),  # Different field name
                        "bounce_rate": campaign.get("bounce_rate", 0),
                        "avg_time_on_site": campaign.get("avg_time_on_site", 0),
                        "revenue": campaign.get("revenue", 0),
                    })
        
        logger.info(f"Successfully fetched {len(result)} records from Matomo")
        return result
    
    except requests.RequestException as e:
        logger.error(f"Error fetching data from Matomo API: {e}")
        logger.error(f"Response content: {e.response.content if hasattr(e, 'response') and e.response else 'No response'}")
        return []

def process_matomo_data(data):
    """
    Process and transform Matomo API data.
    
    Args:
        data (list): List of dictionaries with Matomo data
        
    Returns:
        DataFrame: Processed DataFrame ready for database insertion
    """
    if not data:
        logger.warning("No data to process")
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Convert date strings to datetime objects
    df['date'] = pd.to_datetime(df['date'])
    
    # Format date as string
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    
    # Add source column
    df['source'] = 'matomo'
    
    # Convert numeric fields
    numeric_cols = ['visits', 'unique_visitors', 'page_views', 'bounce_rate', 'avg_time_on_site', 'revenue']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    logger.info(f"Processed {len(df)} Matomo records")
    return df

def store_matomo_data(df):
    """
    Store processed Matomo data in the database.
    
    Args:
        df (DataFrame): DataFrame with processed Matomo data
    """
    if df.empty:
        logger.warning("No data to store")
        return
    
    logger.info(f"Storing {len(df)} records in database")
    
    # Get date and campaign dimensions
    date_dimensions = {}
    campaign_dimensions = {}
    
    with engine.begin() as connection:
        for _, row in df.iterrows():
            date_str = row['date_str']
            campaign_name = row['campaign_name']
            
            # Get or cache dimension IDs
            if date_str not in date_dimensions:
                date_dimensions[date_str] = get_date_dimension_id(date_str)
            
            if campaign_name not in campaign_dimensions:
                campaign_dimensions[campaign_name] = get_campaign_dimension_id(campaign_name)
            
            # Insert fact table record
            query = text("""
                INSERT INTO sm_fact_matomo (
                    date_id, 
                    campaign_id,
                    visits,
                    unique_visitors,
                    page_views,
                    bounce_rate,
                    avg_time_on_site,
                    revenue,
                    source,
                    updated_at
                )
                VALUES (
                    :date_id,
                    :campaign_id,
                    :visits,
                    :unique_visitors,
                    :page_views,
                    :bounce_rate,
                    :avg_time_on_site,
                    :revenue,
                    :source,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (date_id, campaign_id)
                DO UPDATE SET
                    visits = EXCLUDED.visits,
                    unique_visitors = EXCLUDED.unique_visitors,
                    page_views = EXCLUDED.page_views,
                    bounce_rate = EXCLUDED.bounce_rate,
                    avg_time_on_site = EXCLUDED.avg_time_on_site,
                    revenue = EXCLUDED.revenue,
                    source = EXCLUDED.source,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            connection.execute(
                query,
                {
                    "date_id": date_dimensions[date_str],
                    "campaign_id": campaign_dimensions[campaign_name],
                    "visits": row['visits'],
                    "unique_visitors": row['unique_visitors'],
                    "page_views": row['page_views'],
                    "bounce_rate": row['bounce_rate'],
                    "avg_time_on_site": row['avg_time_on_site'],
                    "revenue": row['revenue'],
                    "source": row['source']
                }
            )
    
    logger.info("Matomo data successfully stored in database")

def run_matomo_etl(days_back=3):
    """
    Run the complete ETL process for Matomo data.
    
    Args:
        days_back (int): Number of days to look back for data. Default is 3.
    """
    logger.info(f"Starting Matomo ETL process, looking back {days_back} days")
    
    try:
        # Calculate date range
        end_date = datetime.datetime.now().date()
        start_date = end_date - datetime.timedelta(days=days_back)
        
        # Format as strings
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Extract
        data = fetch_matomo_data(start_date_str, end_date_str)
        
        # Transform
        df = process_matomo_data(data)
        
        # Load
        if not df.empty:
            store_matomo_data(df)
            logger.info("Matomo ETL process completed successfully")
        else:
            logger.warning("No data to store, ETL process completed with warnings")
    
    except Exception as e:
        logger.error(f"Error in Matomo ETL process: {e}", exc_info=True)

def backfill_matomo_data(start_date_str, end_date_str=None):
    """
    Backfill Matomo data for a specific date range.
    
    Args:
        start_date_str (str): Start date in YYYY-MM-DD format
        end_date_str (str, optional): End date in YYYY-MM-DD format. Defaults to yesterday.
    """
    logger.info(f"Starting Matomo backfill from {start_date_str}")
    
    try:
        # Set end date if not provided
        if not end_date_str:
            end_date = datetime.datetime.now().date() - datetime.timedelta(days=1)
            end_date_str = end_date.strftime("%Y-%m-%d")
        
        logger.info(f"Backfilling Matomo data from {start_date_str} to {end_date_str}")
        
        # Extract
        data = fetch_matomo_data(start_date_str, end_date_str)
        
        # Transform
        df = process_matomo_data(data)
        
        # Load
        if not df.empty:
            store_matomo_data(df)
            logger.info(f"Matomo backfill completed successfully: {len(df)} records")
        else:
            logger.warning("No data to backfill")
    
    except Exception as e:
        logger.error(f"Error in Matomo backfill process: {e}", exc_info=True)

def schedule_jobs():
    """
    Schedule the ETL job to run at regular intervals.
    """
    logger.info("Scheduling Matomo data collection jobs")
    
    # Run initial ETL
    run_matomo_etl()
    
    # Schedule daily ETL
    schedule.every(DATA_FETCH_INTERVAL_HOURS).hours.do(run_matomo_etl)
    
    logger.info(f"Jobs scheduled to run every {DATA_FETCH_INTERVAL_HOURS} hours")
    
    # Keep the script running to execute scheduled jobs
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    logger.info("Starting Matomo connector service")
    schedule_jobs()
