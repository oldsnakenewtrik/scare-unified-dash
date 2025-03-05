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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("redtrack_connector")

# Load environment variables
load_dotenv()

# Configuration
REDTRACK_API_KEY = os.getenv("REDTRACK_API_KEY")
REDTRACK_BASE_URL = os.getenv("REDTRACK_BASE_URL", "https://api.redtrack.io")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")
DATA_FETCH_INTERVAL_HOURS = int(os.getenv("DATA_FETCH_INTERVAL_HOURS", "12"))

# Initialize database connection
engine = create_engine(DATABASE_URL)

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
            AND source_system = 'RedTrack'
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
                VALUES (:campaign_name, 'RedTrack', :source_campaign_id, :created_date, :updated_date, TRUE)
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
                AND source_system = 'RedTrack'
            """),
            {"campaign_name": campaign_name}
        ).fetchone()
        
        if result:
            return result[0]
        else:
            raise Exception(f"Failed to create campaign dimension record for {campaign_name}")

def fetch_redtrack_data(start_date, end_date):
    """Fetch data from RedTrack API for the specified date range."""
    logger.info(f"Fetching RedTrack data from {start_date} to {end_date}")
    
    if not REDTRACK_API_KEY:
        logger.error("REDTRACK_API_KEY environment variable is not set")
        return None
    
    try:
        url = f"{REDTRACK_BASE_URL}/report"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {REDTRACK_API_KEY}"
        }
        
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "group": ["campaign", "day"],
            "metrics": ["clicks", "impressions", "conversions", "revenue", "cost", "roi", "ctr", "epc", "cpc"]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from RedTrack API: {str(e)}")
        return None

def process_redtrack_data(data):
    """Process and transform RedTrack API data."""
    if not data or "data" not in data:
        logger.warning("No data to process from RedTrack API")
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(data["data"])
    
    # Rename columns if needed
    if "campaign_name" not in df.columns and "campaign" in df.columns:
        df = df.rename(columns={"campaign": "campaign_name"})
    
    if "date" not in df.columns and "day" in df.columns:
        df = df.rename(columns={"day": "date"})
    
    return df

def store_redtrack_data(df):
    """Store processed RedTrack data in the database."""
    if df.empty:
        logger.warning("No RedTrack data to store")
        return 0
    
    rows_inserted = 0
    
    try:
        with engine.connect() as conn:
            for _, row in df.iterrows():
                # Get dimension IDs
                date_id = get_date_dimension_id(row["date"])
                campaign_id = get_campaign_dimension_id(
                    row["campaign_name"], 
                    source_campaign_id=row.get("campaign_id")
                )
                
                # Check if record already exists
                existing = conn.execute(
                    text("""
                        SELECT redtrack_id 
                        FROM scare_metrics.fact_redtrack 
                        WHERE date_id = :date_id AND campaign_id = :campaign_id
                    """),
                    {"date_id": date_id, "campaign_id": campaign_id}
                ).fetchone()
                
                # Prepare data to insert/update
                fact_data = {
                    "date_id": date_id,
                    "campaign_id": campaign_id,
                    "clicks": int(row.get("clicks", 0)),
                    "impressions": int(row.get("impressions", 0)),
                    "conversions": int(row.get("conversions", 0)),
                    "revenue": float(row.get("revenue", 0)),
                    "cost": float(row.get("cost", 0)),
                    "roi": float(row.get("roi", 0)) if row.get("roi") else None,
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                    "epc": float(row.get("epc", 0)) if row.get("epc") else None,
                    "cpc": float(row.get("cpc", 0)) if row.get("cpc") else None,
                    "source_data": json.dumps(row.to_dict()),
                    "updated_at": datetime.datetime.now()
                }
                
                if existing:
                    # Update existing record
                    update_query = text("""
                        UPDATE scare_metrics.fact_redtrack
                        SET 
                            clicks = :clicks,
                            impressions = :impressions,
                            conversions = :conversions,
                            revenue = :revenue,
                            cost = :cost,
                            roi = :roi,
                            ctr = :ctr,
                            epc = :epc,
                            cpc = :cpc,
                            source_data = :source_data,
                            updated_at = :updated_at
                        WHERE date_id = :date_id AND campaign_id = :campaign_id
                    """)
                    conn.execute(update_query, fact_data)
                else:
                    # Insert new record
                    insert_query = text("""
                        INSERT INTO scare_metrics.fact_redtrack
                        (date_id, campaign_id, clicks, impressions, conversions, revenue, cost, roi, ctr, epc, cpc, source_data, created_at, updated_at)
                        VALUES
                        (:date_id, :campaign_id, :clicks, :impressions, :conversions, :revenue, :cost, :roi, :ctr, :epc, :cpc, :source_data, :updated_at, :updated_at)
                    """)
                    conn.execute(insert_query, fact_data)
                    rows_inserted += 1
            
            conn.commit()
        
        logger.info(f"Successfully stored {rows_inserted} new RedTrack records in the database")
        return rows_inserted
    
    except Exception as e:
        logger.error(f"Error storing RedTrack data: {str(e)}")
        return 0

def run_redtrack_etl():
    """Run the complete ETL process for RedTrack data."""
    logger.info("Starting RedTrack ETL process")
    
    try:
        # Calculate date range (last 3 days by default)
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=3)
        
        # Format dates as strings
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        # Fetch, process, and store data
        raw_data = fetch_redtrack_data(start_date_str, end_date_str)
        processed_data = process_redtrack_data(raw_data)
        records_inserted = store_redtrack_data(processed_data)
        
        logger.info(f"RedTrack ETL process completed successfully. {records_inserted} new records inserted.")
    
    except Exception as e:
        logger.error(f"Error in RedTrack ETL process: {str(e)}")

def schedule_jobs():
    """Schedule the ETL job to run at regular intervals."""
    # Run immediately at startup
    run_redtrack_etl()
    
    # Schedule to run every X hours
    schedule.every(DATA_FETCH_INTERVAL_HOURS).hours.do(run_redtrack_etl)
    
    logger.info(f"Scheduled RedTrack ETL to run every {DATA_FETCH_INTERVAL_HOURS} hours")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Sleep for 1 minute between schedule checks

if __name__ == "__main__":
    logger.info("Starting RedTrack connector service")
    schedule_jobs()
