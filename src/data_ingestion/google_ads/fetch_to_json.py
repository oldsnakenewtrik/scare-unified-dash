"""
Fetch Google Ads data and save it to a JSON file
"""
import os
import json
import logging
import sys
import argparse
from datetime import datetime, timedelta
from main import fetch_google_ads_data, process_google_ads_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_ads_fetch.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("google_ads_fetch")

def fetch_and_save(start_date, end_date, output_dir="./data"):
    """
    Fetch Google Ads data and save it to a JSON file
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        output_dir (str): Directory to save the output file
        
    Returns:
        str: Path to the saved file if successful, None otherwise
    """
    try:
        logger.info(f"Fetching Google Ads data from {start_date} to {end_date}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Fetch data from API
        raw_data = fetch_google_ads_data(start_date, end_date)
        
        if not raw_data:
            logger.warning("No data fetched from Google Ads API")
            return None
        
        logger.info(f"Successfully fetched {len(raw_data)} rows of data")
        
        # Process the data
        processed_data = process_google_ads_data(raw_data)
        logger.info(f"Successfully processed {len(processed_data)} rows of data")
        
        # Save to JSON file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"google_ads_data_{start_date}_to_{end_date}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(processed_data, f, indent=2, default=str)
        
        logger.info(f"Data saved to {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error fetching and saving Google Ads data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Fetch Google Ads data and save to JSON')
    parser.add_argument('--days', type=int, default=7,
                        help='Number of days to fetch data for (default: 7)')
    parser.add_argument('--start-date', type=str,
                        help='Start date (format: YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                        help='End date (format: YYYY-MM-DD)')
    parser.add_argument('--output-dir', type=str, default='./data',
                        help='Directory to save the output file (default: ./data)')
    
    args = parser.parse_args()
    
    # Set dates
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    else:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.days)
        start_date = start_date.strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')
    
    filepath = fetch_and_save(start_date, end_date, args.output_dir)
    
    if filepath:
        logger.info("Data fetching completed successfully")
        print(f"✓ Google Ads data fetched and saved to: {filepath}")
        sys.exit(0)
    else:
        logger.error("Data fetching failed")
        print("✗ Google Ads data fetching failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
