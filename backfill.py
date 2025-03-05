#!/usr/bin/env python3
"""
Backfill script for SCARE Unified Dashboard
This script facilitates backfilling historical data from Google Ads and Bing Ads
"""
import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('backfill')

def validate_date(date_str):
    """
    Validate that a date string is in YYYY-MM-DD format
    
    Args:
        date_str: Date string to validate
        
    Returns:
        bool: True if valid, False if not
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def backfill_google_ads(start_date, end_date):
    """
    Backfill Google Ads data using the Google Ads container
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    logger.info(f"Starting Google Ads backfill from {start_date} to {end_date}")
    
    command = [
        "docker-compose", 
        "run", 
        "--rm", 
        "google_ads", 
        "python", 
        "/app/main.py", 
        "--backfill", 
        "--start-date", start_date
    ]
    
    if end_date:
        command.extend(["--end-date", end_date])
        
    try:
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info("Google Ads backfill completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Google Ads backfill failed: {e}")
        if e.stdout:
            logger.error(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")

def backfill_bing_ads(start_date, end_date):
    """
    Backfill Bing Ads data using the Bing Ads container
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    logger.info(f"Starting Bing Ads backfill from {start_date} to {end_date}")
    
    command = [
        "docker-compose", 
        "run", 
        "--rm", 
        "bing_ads", 
        "python", 
        "/app/main.py", 
        "--backfill", 
        "--start-date", start_date
    ]
    
    if end_date:
        command.extend(["--end-date", end_date])
        
    try:
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info("Bing Ads backfill completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Bing Ads backfill failed: {e}")
        if e.stdout:
            logger.error(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")

def main():
    """Main function to run the backfill script with command line arguments"""
    parser = argparse.ArgumentParser(description="Backfill data for SCARE Unified Dashboard")
    parser.add_argument("--start-date", required=True, help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for backfill (YYYY-MM-DD)")
    parser.add_argument("--source", choices=["google", "bing", "all"], default="all", 
                      help="Data source to backfill (google, bing, or all)")
    
    args = parser.parse_args()
    
    # Validate dates
    if not validate_date(args.start_date):
        logger.error(f"Invalid start date format: {args.start_date}. Use YYYY-MM-DD format.")
        sys.exit(1)
        
    if args.end_date and not validate_date(args.end_date):
        logger.error(f"Invalid end date format: {args.end_date}. Use YYYY-MM-DD format.")
        sys.exit(1)
    
    # Run backfill for selected sources
    if args.source in ["google", "all"]:
        backfill_google_ads(args.start_date, args.end_date)
        
    if args.source in ["bing", "all"]:
        backfill_bing_ads(args.start_date, args.end_date)
    
    logger.info("Backfill operations completed")

if __name__ == "__main__":
    main()
