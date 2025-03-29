#!/usr/bin/env python3
"""
Bing Ads API integration for SCARE Unified Dashboard
"""
import os
import time
import json
import logging
import datetime
import argparse
import sys # Added sys for exit codes
import pandas as pd
from sqlalchemy import create_engine, text
from bingads.service_client import ServiceClient
from bingads.authorization import AuthorizationData # Removed OAuthWebAuthCodeGrant as we use refresh token flow
from bingads.v13.reporting import ReportingDownloadParameters # ReportingServiceManager is implicitly used via ServiceClient
# Removed redundant import of ReportingServiceManager
import xml.etree.ElementTree as ET
import tempfile
from token_refresh import get_access_token, refresh_token # Removed get_refresh_token
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
BING_ADS_REFRESH_TOKEN = os.getenv('BING_ADS_REFRESH_TOKEN') # Initial refresh token
BING_ADS_ACCOUNT_ID = os.getenv('BING_ADS_ACCOUNT_ID')
BING_ADS_CUSTOMER_ID = os.getenv('BING_ADS_CUSTOMER_ID') # Customer ID is needed
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
    Get authentication data for Bing Ads API using refreshed token.

    Returns:
        AuthorizationData object or None if authentication fails.
    """
    try:
        access_token = get_access_token()
        if not access_token:
            logger.error("Failed to get a valid access token for Bing Ads. Ensure token refresh succeeded.")
            sys.exit(1) # Exit on failure

        if not all([BING_ADS_DEVELOPER_TOKEN, BING_ADS_CLIENT_ID, BING_ADS_ACCOUNT_ID, BING_ADS_CUSTOMER_ID]):
            logger.error("Missing required Bing Ads API credentials (Developer Token, Client ID, Account ID, Customer ID)")
            sys.exit(1) # Exit on failure

        auth_data = AuthorizationData(
            account_id=BING_ADS_ACCOUNT_ID,
            customer_id=BING_ADS_CUSTOMER_ID, # Customer ID is required for AuthorizationData
            developer_token=BING_ADS_DEVELOPER_TOKEN,
            authentication=None # Set below
        )

        # Set the authentication directly with the OAuth access token
        auth_data.authentication = {
            'access_token': access_token,
            'client_id': BING_ADS_CLIENT_ID # Include client_id here for clarity, though primarily used in refresh
        }

        logger.info("Successfully created Bing Ads authentication data.")
        return auth_data
    except Exception as e:
        logger.error(f"Error creating Bing Ads authentication data: {e}")
        sys.exit(1) # Exit on failure

def get_db_connection():
    """
    Create a database connection engine.

    Returns:
        SQLAlchemy engine object or exits on failure.
    """
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        logger.warning("DATABASE_URL not set. Falling back to individual DB variables (DB_HOST, DB_USER, etc.).")
        if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
             logger.error("Missing required database connection details (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)")
             sys.exit(1)
        connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        if connection_string.startswith("postgres://"):
             connection_string = connection_string.replace("postgres://", "postgresql://", 1)
        logger.info("Using DATABASE_URL for database connection.")

    try:
        engine = create_engine(connection_string)
        logger.info(f"Attempting database connection to {engine.url.render_as_string(hide_password=True)}")
        # Test connection
        with engine.connect() as connection:
            logger.info("Database connection successful.")
        return engine
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1) # Exit on failure

def download_bing_ads_report(auth_data, start_date, end_date):
    """
    Download campaign performance report from Bing Ads.

    Args:
        auth_data: Bing Ads authorization data.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        Path to downloaded report file or exits on failure.
    """
    report_file_path = os.path.join(REPORTS_DIR, f"bing_ads_report_{start_date}_to_{end_date}.csv")

    try:
        # Initialize the Reporting Service Client
        reporting_service = ServiceClient(
            service='Reporting',
            version=13,
            authorization_data=auth_data,
            environment='production',
        )

        # Define the report request using the service client's factory
        report_request = reporting_service.factory.create('CampaignPerformanceReportRequest')
        report_request.Format = 'Csv'
        report_request.ReturnOnlyCompleteData = False
        report_request.Aggregation = 'Daily'

        # Set the time period
        report_time = reporting_service.factory.create('ReportTime')
        start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')

        report_time.CustomDateRangeStart = reporting_service.factory.create('Date')
        report_time.CustomDateRangeStart.Day = start_dt.day
        report_time.CustomDateRangeStart.Month = start_dt.month
        report_time.CustomDateRangeStart.Year = start_dt.year

        report_time.CustomDateRangeEnd = reporting_service.factory.create('Date')
        report_time.CustomDateRangeEnd.Day = end_dt.day
        report_time.CustomDateRangeEnd.Month = end_dt.month
        report_time.CustomDateRangeEnd.Year = end_dt.year

        report_request.Time = report_time

        # Define Scope (Account IDs)
        report_scope = reporting_service.factory.create('AccountThroughCampaignReportScope')
        report_scope.AccountIds = [int(BING_ADS_ACCOUNT_ID)] # Assign Python list directly
        report_request.Scope = report_scope

        # Set the columns to include
        report_columns = reporting_service.factory.create('ArrayOfCampaignPerformanceReportColumn')
        # Corrected way to append columns
        columns_to_add = [
            'TimePeriod',
            'AccountId',
            'AccountName',
            'CampaignId',
            'CampaignName',
            'CampaignStatus',
            'Impressions',
            'Clicks',
            'Spend',
            'Conversions', # Check if this is the correct Bing Ads name (might be 'AllConversions')
            'Revenue', # Check if this is the correct Bing Ads name (might be 'AllRevenue')
            'AverageCpc',
            'CostPerConversion' # Check if this is the correct Bing Ads name (might be 'CostPerAllConversion')
        ]
        for col in columns_to_add:
             report_columns.CampaignPerformanceReportColumn.append(col)
        report_request.Columns = report_columns

        # Submit and download the report using ReportingDownloadParameters
        reporting_download_parameters = ReportingDownloadParameters(
            report_request=report_request,
            result_file_directory=REPORTS_DIR, # Use the specified directory
            result_file_name=os.path.basename(report_file_path), # Just the filename
            overwrite_result_file=True,
            # Optional: Set timeout in milliseconds
            timeout_in_milliseconds = 3600000 # 1 hour
        )

        # Use the helper function from the SDK
        # Need ReportingServiceManager instance for download_report helper
        reporting_service_manager = ReportingServiceManager(
            authorization_data=auth_data,
            poll_interval_in_milliseconds=5000,
            environment='production'
        )

        logger.info(f"Submitting report request for {start_date} to {end_date}")
        # The download_report function handles polling and downloading
        report_container = reporting_service_manager.download_report(reporting_download_parameters)

        if report_container and report_container.report_file_path:
            # Ensure the downloaded file matches the expected path
            # The SDK might add suffixes, so we need the actual path returned
            actual_report_path = report_container.report_file_path
            logger.info(f"Report successfully downloaded to {actual_report_path}")
            # If the path differs, move/rename it to our standard name for consistency
            if actual_report_path != report_file_path:
                try:
                    os.rename(actual_report_path, report_file_path)
                    logger.info(f"Renamed downloaded report to {report_file_path}")
                    actual_report_path = report_file_path
                except OSError as move_error:
                    logger.warning(f"Could not rename report from {actual_report_path} to {report_file_path}: {move_error}")
            return actual_report_path
        else:
            logger.warning("Report download did not return a valid file path or container.")
            # If the download 'succeeds' but returns no path, treat it as failure for data processing
            sys.exit(1) # Exit as we expected data but got none

    except Exception as e:
        logger.error(f"Error downloading Bing Ads report: {e}", exc_info=True)
        sys.exit(1) # Exit on failure

def parse_bing_ads_report(report_file_path):
    """
    Parse Bing Ads report CSV into pandas DataFrame.

    Args:
        report_file_path: Path to the downloaded report CSV.

    Returns:
        pandas DataFrame or exits on failure.
    """
    try:
        # Read the CSV, skipping metadata rows (usually first 10 for Bing)
        # Need to dynamically find the start of the data
        with open(report_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        # Find the header row (e.g., starts with "TimePeriod")
        data_start_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('"TimePeriod"'): # Headers are usually quoted
                data_start_line = i
                break
        else:
            # Handle cases where the header isn't found or format is unexpected
            if len(lines) > 1 and lines[0].strip().startswith('Report Name:'):
                 # Common format, try a fixed skip (adjust if needed)
                 data_start_line = 10 # Example skip count
                 logger.warning(f"Could not find header row starting with 'TimePeriod'. Assuming data starts after line {data_start_line}.")
            else:
                 logger.error(f"Could not determine data start line in report: {report_file_path}")
                 # Check if file is empty or very small
                 if os.path.getsize(report_file_path) < 50:
                     logger.warning(f"Report file {report_file_path} seems empty or too small. Treating as no data.")
                     return pd.DataFrame() # Return empty DataFrame
                 else:
                     logger.error("Exiting due to inability to parse report structure.")
                     sys.exit(1)

        # Read the CSV data
        df = pd.read_csv(report_file_path, skiprows=data_start_line)

        # Basic Cleaning & Renaming
        df.columns = [col.replace(' ', '').replace('(GregorianDate)', '') for col in df.columns] # Remove spaces and specific suffixes
        df = df.rename(columns={
            'TimePeriod': 'date',
            'AccountId': 'account_id',
            'AccountName': 'account_name',
            'CampaignId': 'campaign_id',
            'CampaignName': 'campaign_name',
            'CampaignStatus': 'campaign_status',
            'Spend': 'cost', # Rename Spend to cost for consistency
            'Conversions': 'conversions', # Assuming 'Conversions' is the correct column name
            'Revenue': 'revenue', # Assuming 'Revenue' is the correct column name
            # Ensure types are correct
        })

        # Type Conversion
        df['date'] = pd.to_datetime(df['date']).dt.date
        numeric_cols = ['Impressions', 'Clicks', 'cost', 'conversions', 'revenue', 'AverageCpc', 'CostPerConversion']
        for col in numeric_cols:
            if col in df.columns:
                 # Remove commas and convert to numeric, coerce errors to NaN
                 if df[col].dtype == 'object':
                     df[col] = df[col].astype(str).str.replace(',', '', regex=False)
                 df[col] = pd.to_numeric(df[col], errors='coerce')

        # Handle potential NaN values from conversion errors or missing data
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # Add platform column
        df['platform'] = 'Bing Ads'

        # Select and reorder columns for database insertion
        final_columns = [
            'date', 'platform', 'account_id', 'account_name',
            'campaign_id', 'campaign_name', 'campaign_status',
            'Impressions', 'Clicks', 'cost', 'conversions', 'revenue'
        ]
        # Ensure all expected columns exist, add if missing and fill with 0 or default
        for col in final_columns:
            if col not in df.columns:
                logger.warning(f"Column '{col}' not found in report, adding with default value.")
                if col in ['account_id', 'campaign_id']:
                    df[col] = 0 # Or appropriate default
                elif col in ['account_name', 'campaign_name', 'campaign_status', 'platform']: 
                    df[col] = '' # Or appropriate default
                else:
                    df[col] = 0 # Default for numeric

        df = df[final_columns]

        logger.info(f"Successfully parsed {len(df)} rows from Bing Ads report.")
        return df
    except pd.errors.EmptyDataError:
        logger.warning(f"Report file {report_file_path} is empty after skipping headers. No data to parse.")
        return pd.DataFrame() # Return empty DataFrame
    except Exception as e:
        logger.error(f"Error parsing Bing Ads report {report_file_path}: {e}", exc_info=True)
        sys.exit(1) # Exit on failure

def store_bing_ads_data(data):
    """
    Store Bing Ads data in the database, handling potential conflicts.

    Args:
        data: DataFrame with Bing Ads data.
    """
    if data.empty:
        logger.info("No Bing Ads data to store.")
        return

    engine = get_db_connection()
    if not engine:
        logger.error("Cannot store data, database connection failed.")
        sys.exit(1) # Exit if connection failed earlier

    # Ensure date column is string for SQL compatibility if needed, though pandas handles it
    data['date'] = data['date'].astype(str)

    # Prepare data for insertion (convert DataFrame to list of dicts)
    records = data.to_dict(orient='records')

    # SQL for UPSERT
    upsert_sql = text("""
        INSERT INTO fact_bing_ads (
            date, platform, account_id, account_name, campaign_id, campaign_name,
            campaign_status, impressions, clicks, cost, conversions, revenue
        )
        VALUES (
            :date, :platform, :account_id, :account_name, :campaign_id, :campaign_name,
            :campaign_status, :impressions, :clicks, :cost, :conversions, :revenue
        )
        ON CONFLICT (date, campaign_id) DO UPDATE SET
            platform = EXCLUDED.platform,
            account_id = EXCLUDED.account_id,
            account_name = EXCLUDED.account_name,
            campaign_name = EXCLUDED.campaign_name,
            campaign_status = EXCLUDED.campaign_status,
            impressions = EXCLUDED.impressions,
            clicks = EXCLUDED.clicks,
            cost = EXCLUDED.cost,
            conversions = EXCLUDED.conversions,
            revenue = EXCLUDED.revenue,
            last_updated = NOW();
    """)

    rows_affected = 0
    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                for record in records:
                    # Ensure keys match bind parameters in SQL
                    sql_params = {
                        'date': record['date'],
                        'platform': record['platform'],
                        'account_id': record['account_id'],
                        'account_name': record['account_name'],
                        'campaign_id': record['campaign_id'],
                        'campaign_name': record['campaign_name'],
                        'campaign_status': record['campaign_status'],
                        'impressions': record['Impressions'], # Use correct case from DataFrame
                        'clicks': record['Clicks'],
                        'cost': record['cost'],
                        'conversions': record['conversions'],
                        'revenue': record['revenue']
                    }
                    connection.execute(upsert_sql, sql_params)
                    rows_affected += 1 # Count executions, not actual rows inserted/updated
        logger.info(f"Successfully executed upsert for {rows_affected} Bing Ads records.")
    except Exception as e:
        logger.error(f"Error storing Bing Ads data: {e}", exc_info=True)
        sys.exit(1) # Exit on failure

def fetch_and_store_range(start_date, end_date):
    """
    Fetches and stores Bing Ads data for a given date range.

    Args:
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
    """
    logger.info(f"Starting Bing Ads data fetch for range: {start_date} to {end_date}")

    # 1. Authentication
    auth_data = get_auth_data()
    # get_auth_data now exits on failure, no need to check return

    # 2. Download Report
    report_path = download_bing_ads_report(auth_data, start_date, end_date)
    # download_bing_ads_report now exits on failure

    # 3. Parse Report
    data = parse_bing_ads_report(report_path)
    # parse_bing_ads_report now exits on failure or returns empty DF

    # 4. Store Data
    if data is not None and not data.empty:
        store_bing_ads_data(data)
        # store_bing_ads_data now exits on failure
        logger.info(f"Successfully processed Bing Ads data for range: {start_date} to {end_date}")
    elif data is not None and data.empty:
         logger.info(f"No Bing Ads data found for range: {start_date} to {end_date}. Nothing to store.")
    # No else needed, previous steps exit on error

def main():
    """
    Main function to run the Bing Ads connector based on arguments.
    Handles token refresh, argument parsing, and calling fetch/store logic.
    Exits with non-zero code on failure.
    """
    parser = argparse.ArgumentParser(description="Bing Ads data connector for SCARE Dashboard")
    parser.add_argument("--run-once", action="store_true", help="Run a single fetch for a specified number of past days.")
    parser.add_argument("--days", type=int, default=7, help="Number of past days to fetch data for when using --run-once (default: 7).")
    parser.add_argument("--backfill", action="store_true", help="Run a historical data backfill for a specific date range.")
    parser.add_argument("--start-date", help="Start date for backfill (YYYY-MM-DD). Required if --backfill is used.")
    parser.add_argument("--end-date", help="End date for backfill (YYYY-MM-DD). Optional for --backfill, defaults to yesterday.")
    args = parser.parse_args()

    try:
        # Always ensure token is refreshed before proceeding
        logger.info("Attempting to refresh Bing Ads token...")
        if not refresh_token():
            logger.error("Failed to refresh Bing Ads token. Cannot proceed.")
            sys.exit(1)
        logger.info("Bing Ads token refreshed successfully.")

        if args.run_once:
            logger.info(f"Running in --run-once mode for the last {args.days} days.")
            end_date_dt = datetime.datetime.now() - datetime.timedelta(days=1)
            start_date_dt = end_date_dt - datetime.timedelta(days=args.days - 1)
            start_date_str = start_date_dt.strftime("%Y-%m-%d")
            end_date_str = end_date_dt.strftime("%Y-%m-%d")
            fetch_and_store_range(start_date_str, end_date_str)
        elif args.backfill:
            if not args.start_date:
                logger.error("Error: --start-date is required when using --backfill.")
                sys.exit(1)
            end_date_str = args.end_date
            if not end_date_str:
                end_date_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"Running in --backfill mode from {args.start_date} to {end_date_str}.")
            fetch_and_store_range(args.start_date, end_date_str)
        else:
            logger.error("Error: No operation mode specified. Use --run-once or --backfill.")
            parser.print_help()
            sys.exit(1)

        logger.info("Bing Ads script completed successfully.")
        sys.exit(0) # Explicitly exit with 0 on success

    except Exception as e:
        # Catch any unexpected errors in main execution flow
        logger.error(f"An unexpected error occurred in main execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
