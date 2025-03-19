"""
Run the Google Ads ETL process
"""
import sys
import logging
from datetime import datetime, timedelta
import argparse
from main import run_google_ads_etl, backfill_google_ads_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_ads_etl_run.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("google_ads_etl_run")

def main():
    """Main function to run the ETL process"""
    parser = argparse.ArgumentParser(description='Run Google Ads ETL process')
    parser.add_argument('--days', type=int, default=3,
                        help='Number of days to fetch data for (default: 3)')
    parser.add_argument('--backfill', action='store_true',
                        help='Run a backfill instead of regular ETL')
    parser.add_argument('--start-date', type=str,
                        help='Start date for backfill (format: YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                        help='End date for backfill (format: YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.backfill:
        if not args.start_date:
            logger.error("--start-date is required for backfill")
            sys.exit(1)
            
        logger.info(f"Running Google Ads backfill from {args.start_date} to {args.end_date or 'today'}")
        success = backfill_google_ads_data(args.start_date, args.end_date)
    else:
        logger.info(f"Running Google Ads ETL for the last {args.days} days")
        success = run_google_ads_etl(args.days)
    
    if success:
        logger.info("ETL process completed successfully")
        print("✓ Google Ads ETL process completed successfully")
        sys.exit(0)
    else:
        logger.error("ETL process failed")
        print("✗ Google Ads ETL process failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
