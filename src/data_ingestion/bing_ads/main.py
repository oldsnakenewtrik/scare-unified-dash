#!/usr/bin/env python3
"""
Bing Ads API integration for SCARE Unified Dashboard
"""
import os
import time
import logging
import datetime
import argparse
import schedule
import pandas as pd
from sqlalchemy import create_engine, text
from bingads.service_client import ServiceClient
from bingads.authorization import AuthorizationData, OAuthWebAuthCodeGrant
from bingads.v13.reporting import ReportingServiceManager, ReportingDownloadParameters
from bingads.v13.reporting.reporting_service_manager import ReportingServiceManager
import xml.etree.ElementTree as ET
import tempfile
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bing_ads_connector')

# Environment variables and constants
BING_ADS_DEVELOPER_TOKEN = os.getenv('BING_ADS_DEVELOPER_TOKEN')
BING_ADS_CLIENT_ID = os.getenv('BING_ADS_CLIENT_ID')
BING_ADS_CLIENT_SECRET = os.getenv('BING_ADS_CLIENT_SECRET')
BING_ADS_REFRESH_TOKEN = os.getenv('BING_ADS_REFRESH_TOKEN')
BING_ADS_ACCOUNT_ID = os.getenv('BING_ADS_ACCOUNT_ID')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'scare_dash')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
REPORTS_DIR = os.getenv('REPORTS_DIR', '/app/reports')

# Create reports directory if it doesn't exist
os.makedirs(REPORTS_DIR, exist_ok=True)

def get_auth_data():
    """
    Get Bing Ads authentication data
    
    Returns:
        AuthorizationData: Authorization data for Bing Ads API
    """
    try:
        authorization_data = AuthorizationData(
            account_id=BING_ADS_ACCOUNT_ID,
            customer_id=None,
            developer_token=BING_ADS_DEVELOPER_TOKEN,
            authentication=None
        )
        
        oauth_web_auth_code_grant = OAuthWebAuthCodeGrant(
            client_id=BING_ADS_CLIENT_ID,
            client_secret=BING_ADS_CLIENT_SECRET,
            redirection_uri="https://login.microsoftonline.com/common/oauth2/nativeclient"
        )
        
        oauth_web_auth_code_grant.request_oauth_tokens_by_refresh_token(BING_ADS_REFRESH_TOKEN)
        authorization_data.authentication = oauth_web_auth_code_grant
        
        logger.info("Bing Ads authentication successful")
        return authorization_data
    except Exception as e:
        logger.error(f"Bing Ads authentication failed: {e}")
        return None

def get_db_connection():
    """
    Create a database connection
    
    Returns:
        SQLAlchemy engine connection
    """
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    try:
        engine = create_engine(connection_string)
        logger.info("Database connection established")
        return engine
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

def download_bing_ads_report(auth_data, start_date, end_date):
    """
    Download campaign performance report from Bing Ads
    
    Args:
        auth_data: Bing Ads authorization data
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Path to downloaded report file
    """
    try:
        report_file_path = os.path.join(REPORTS_DIR, f"bing_ads_report_{start_date}_to_{end_date}.csv")
        
        reporting_service_manager = ReportingServiceManager(
            authorization_data=auth_data,
            poll_interval_in_milliseconds=5000,
            environment='production',
        )
        
        # Define the report request
        report_request = reporting_service_manager.factory.create('CampaignPerformanceReportRequest')
        report_request.Format = 'Csv'
        report_request.ReturnOnlyCompleteData = False
        report_request.Aggregation = 'Daily'
        
        # Set the time period
        report_time = reporting_service_manager.factory.create('ReportTime')
        report_time.CustomDateRangeStart = reporting_service_manager.factory.create('Date')
        report_time.CustomDateRangeStart.Day = int(start_date.split('-')[2])
        report_time.CustomDateRangeStart.Month = int(start_date.split('-')[1])
        report_time.CustomDateRangeStart.Year = int(start_date.split('-')[0])
        
        report_time.CustomDateRangeEnd = reporting_service_manager.factory.create('Date')
        report_time.CustomDateRangeEnd.Day = int(end_date.split('-')[2])
        report_time.CustomDateRangeEnd.Month = int(end_date.split('-')[1])
        report_time.CustomDateRangeEnd.Year = int(end_date.split('-')[0])
        
        report_request.Time = report_time
        
        # Set the columns to include
        report_columns = reporting_service_manager.factory.create('ArrayOfCampaignPerformanceReportColumn')
        report_columns.CampaignPerformanceReportColumn.append([
            'TimePeriod',
            'AccountId',
            'AccountName',
            'CampaignId',
            'CampaignName',
            'CampaignStatus',
            'Impressions',
            'Clicks',
            'Spend',
            'Conversions',
            'Revenue',
            'AverageCpc',
            'CostPerConversion'
        ])
        report_request.Columns = report_columns
        
        # Submit and download the report
        reporting_download_parameters = ReportingDownloadParameters(
            report_request=report_request,
            result_file_directory=REPORTS_DIR,
            result_file_name=os.path.basename(report_file_path),
            overwrite_result_file=True
        )
        
        report_container = reporting_service_manager.download_report(reporting_download_parameters)
        if report_container is not None:
            logger.info(f"Report downloaded to {report_file_path}")
            return report_file_path
        else:
            logger.warning("No report data available")
            return None
    except Exception as e:
        logger.error(f"Error downloading Bing Ads report: {e}")
        return None

def parse_bing_ads_report(report_file_path):
    """
    Parse Bing Ads report CSV into pandas DataFrame
    
    Args:
        report_file_path: Path to the downloaded report file
        
    Returns:
        DataFrame with Bing Ads data
    """
    try:
        if not os.path.exists(report_file_path):
            logger.error(f"Report file not found: {report_file_path}")
            return None
            
        # Skip the header rows which contain metadata
        with open(report_file_path, 'r', encoding='utf-8-sig') as f:
            # Count header rows to skip
            line = f.readline()
            header_rows = 0
            while not line.startswith('TimePeriod') and header_rows < 10:
                header_rows += 1
                line = f.readline()
                
        # Read the CSV with pandas
        df = pd.read_csv(report_file_path, skiprows=header_rows)
        
        # Process and clean the data
        if 'TimePeriod' in df.columns:
            # Convert to ISO date format
            df['date'] = pd.to_datetime(df['TimePeriod']).dt.strftime('%Y-%m-%d')
            df.drop('TimePeriod', axis=1, inplace=True)
        else:
            logger.error("TimePeriod column not found in report")
            return None
            
        # Rename columns to match database schema
        df.rename(columns={
            'AccountId': 'account_id',
            'AccountName': 'account_name',
            'CampaignId': 'campaign_id',
            'CampaignName': 'campaign_name',
            'CampaignStatus': 'campaign_status',
            'Impressions': 'impressions',
            'Clicks': 'clicks',
            'Spend': 'cost',
            'AverageCpc': 'average_cpc',
            'Conversions': 'conversions'
        }, inplace=True)
        
        # Add source column
        df['source'] = 'bing_ads'
        df['updated_at'] = datetime.datetime.now()
        
        logger.info(f"Parsed {len(df)} rows from Bing Ads report")
        return df
    except Exception as e:
        logger.error(f"Error parsing Bing Ads report: {e}")
        return None

def store_bing_ads_data(data):
    """
    Store Bing Ads data in the database
    
    Args:
        data: DataFrame with Bing Ads data
    """
    engine = get_db_connection()
    if not engine:
        return
    
    try:
        # Create the fact_bing_ads table if it doesn't exist
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS scare_metrics.fact_bing_ads (
                    id SERIAL PRIMARY KEY,
                    date VARCHAR(10) NOT NULL,
                    campaign_id VARCHAR(50),
                    campaign_name VARCHAR(255),
                    account_id VARCHAR(50),
                    account_name VARCHAR(255),
                    impressions INTEGER,
                    clicks INTEGER,
                    cost DECIMAL(18,2),
                    average_cpc DECIMAL(18,2),
                    conversions DECIMAL(10,2),
                    source VARCHAR(50),
                    updated_at TIMESTAMP
                )
            """))
        
        # Insert data into the fact_bing_ads table
        with engine.begin() as conn:
            for _, row in data.iterrows():
                # Check if record exists
                result = conn.execute(
                    text("""
                        SELECT id FROM scare_metrics.fact_bing_ads
                        WHERE date = :date AND campaign_id = :campaign_id
                    """),
                    {
                        "date": row.get("date"),
                        "campaign_id": row.get("campaign_id")
                    }
                ).fetchone()
                
                if result:
                    # Update existing record
                    conn.execute(
                        text("""
                            UPDATE scare_metrics.fact_bing_ads SET
                                impressions = :impressions,
                                clicks = :clicks,
                                cost = :cost,
                                average_cpc = :average_cpc,
                                conversions = :conversions,
                                updated_at = :updated_at
                            WHERE id = :id
                        """),
                        {
                            "id": result[0],
                            "impressions": int(row.get("impressions", 0)),
                            "clicks": int(row.get("clicks", 0)),
                            "cost": float(row.get("cost", 0)),
                            "average_cpc": float(row.get("average_cpc", 0)),
                            "conversions": float(row.get("conversions", 0)),
                            "updated_at": datetime.datetime.now()
                        }
                    )
                else:
                    # Insert new record
                    conn.execute(
                        text("""
                            INSERT INTO scare_metrics.fact_bing_ads
                            (date, campaign_id, campaign_name, account_id, account_name, impressions, clicks, cost, average_cpc, conversions, source, updated_at)
                            VALUES
                            (:date, :campaign_id, :campaign_name, :account_id, :account_name, :impressions, :clicks, :cost, :average_cpc, :conversions, :source, :updated_at)
                        """),
                        {
                            "date": row.get("date"),
                            "campaign_id": row.get("campaign_id"),
                            "campaign_name": row.get("campaign_name"),
                            "account_id": row.get("account_id"),
                            "account_name": row.get("account_name"),
                            "impressions": int(row.get("impressions", 0)),
                            "clicks": int(row.get("clicks", 0)),
                            "cost": float(row.get("cost", 0)),
                            "average_cpc": float(row.get("average_cpc", 0)),
                            "conversions": float(row.get("conversions", 0)),
                            "source": row.get("source"),
                            "updated_at": datetime.datetime.now()
                        }
                    )
                
        logger.info(f"Successfully stored {len(data)} rows of Bing Ads data")
    except Exception as e:
        logger.error(f"Error storing Bing Ads data: {e}")

def fetch_and_store_daily_data():
    """
    Fetch yesterday's data and store it in the database
    """
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(f"Fetching Bing Ads data for {yesterday}")
    
    auth_data = get_auth_data()
    if not auth_data:
        return
    
    report_path = download_bing_ads_report(auth_data, yesterday, yesterday)
    if report_path:
        data = parse_bing_ads_report(report_path)
        if data is not None and not data.empty:
            store_bing_ads_data(data)
            logger.info(f"Successfully processed Bing Ads data for {yesterday}")
        else:
            logger.warning(f"No Bing Ads data available for {yesterday}")
    else:
        logger.warning(f"Failed to download Bing Ads report for {yesterday}")

def backfill_bing_ads_data(start_date, end_date=None):
    """
    Backfill Bing Ads data for a specific date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format. Defaults to yesterday.
    """
    if end_date is None:
        end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
    logger.info(f"Starting Bing Ads backfill from {start_date} to {end_date}")
    
    auth_data = get_auth_data()
    if not auth_data:
        logger.error("Failed to authenticate with Bing Ads")
        return
    
    report_path = download_bing_ads_report(auth_data, start_date, end_date)
    if report_path:
        data = parse_bing_ads_report(report_path)
        if data is not None and not data.empty:
            store_bing_ads_data(data)
            logger.info(f"Successfully backfilled Bing Ads data from {start_date} to {end_date}")
        else:
            logger.warning(f"No Bing Ads data retrieved for backfill period")
    else:
        logger.warning(f"Failed to download Bing Ads report for backfill period")

def check_api_health():
    """
    Check the health of the Bing Ads API connection
    """
    auth_data = get_auth_data()
    if auth_data:
        logger.info("Bing Ads API connection is healthy")
        return True
    else:
        logger.error("Bing Ads API connection check failed")
        return False

def setup_schedule():
    """
    Set up scheduled jobs
    """
    # Regular daily updates at 4 AM (offset from Google Ads to distribute load)
    schedule.every().day.at("04:00").do(fetch_and_store_daily_data)
    
    # Weekly health check at 1:30 AM on Mondays (offset from Google Ads)
    schedule.every().monday.at("01:30").do(check_api_health)

    logger.info("Scheduled jobs have been set up")

def main():
    """
    Main function to run the Bing Ads connector
    """
    parser = argparse.ArgumentParser(description="Bing Ads data connector")
    parser.add_argument("--backfill", action="store_true", help="Run in backfill mode")
    parser.add_argument("--start-date", help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for backfill (YYYY-MM-DD)")
    args = parser.parse_args()
    
    if args.backfill:
        if not args.start_date:
            logger.error("Start date required for backfill")
            return
        backfill_bing_ads_data(args.start_date, args.end_date)
    else:
        # Set up regular schedule and run indefinitely
        setup_schedule()
        logger.info("Starting scheduled jobs...")
        
        # Run once immediately
        fetch_and_store_daily_data()
        
        # Keep the script running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Process interrupted, shutting down")

if __name__ == "__main__":
    main()
