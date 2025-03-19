#!/usr/bin/env python

import os
import sys
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('google_ads_fetch_only')

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

def get_google_ads_client():
    """Create and return a Google Ads API client."""
    try:
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
        logger.info("Successfully created Google Ads client")
        return client
    except Exception as e:
        logger.error(f"Error creating Google Ads client: {str(e)}")
        return None

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
        ga_service = client.get_service("GoogleAdsService")
        
        # Construct the query to fetch campaign metrics
        query = f"""
            SELECT
              campaign.id,
              campaign.name,
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
        
        logger.info(f"Executing Google Ads query...")
        
        # Execute the query and stream results
        response = ga_service.search_stream(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)
        
        # Process the results
        campaign_data = []
        
        for batch in response:
            for row in batch.results:
                # Extract data from the row and handle fields carefully to avoid None errors
                data = {
                    "campaign_id": row.campaign.id,
                    "campaign_name": row.campaign.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": row.metrics.cost_micros / 1_000_000,  # Convert from micros to dollars
                    "date": row.segments.date
                }
                
                # Handle potentially missing or null metric fields
                if hasattr(row.metrics, 'average_cpc') and row.metrics.average_cpc:
                    data["average_cpc"] = row.metrics.average_cpc.value / 1_000_000 if hasattr(row.metrics.average_cpc, 'value') else 0
                else:
                    data["average_cpc"] = 0
                    
                data["conversions"] = row.metrics.conversions if hasattr(row.metrics, 'conversions') else 0
                data["conversions_value"] = row.metrics.conversions_value if hasattr(row.metrics, 'conversions_value') else 0
                
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

def save_to_csv(data, output_file='campaign_data.csv'):
    """Save the campaign data to a CSV file."""
    if not data:
        logger.warning("No data to save to CSV")
        return False
        
    try:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(data)
        
        # Calculate CTR and average CPC if not present
        if 'ctr' not in df.columns:
            df['ctr'] = df.apply(lambda row: (row['clicks'] / row['impressions'] * 100) if row['impressions'] > 0 else 0, axis=1)
        
        if 'average_cpc' not in df.columns:
            df['average_cpc'] = df.apply(lambda row: (row['cost'] / row['clicks']) if row['clicks'] > 0 else 0, axis=1)
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Data saved to {output_file}")
        
        # Calculate and log summary stats
        logger.info(f"Summary by campaign: (first 20 rows):")
        campaign_summary = df.groupby('campaign_name').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'cost': 'sum',
            'ctr': 'mean',
            'average_cpc': 'mean',
            'conversions': 'sum'
        }).reset_index()
        
        for idx, row in campaign_summary.head(20).iterrows():
            logger.info(f"{row['campaign_name']}: {int(row['impressions'])} impressions, {int(row['clicks'])} clicks, ${row['cost']:.2f} cost, {row['ctr']:.2f}% CTR, ${row['average_cpc']:.2f} avg CPC, {row['conversions']} conversions")
            
        return True
    except Exception as e:
        logger.error(f"Error saving data to CSV: {str(e)}")
        return False

def main():
    """Main function"""
    # Default to last 30 days
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)
    
    # Format dates
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    # Fetch data
    data = fetch_google_ads_data(start_date_str, end_date_str)
    
    # Save to CSV
    if data:
        save_to_csv(data, 'google_ads_data.csv')
        
        # Also save raw JSON for inspection
        with open('google_ads_data.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
            logger.info("Raw data saved to google_ads_data.json")
    else:
        logger.warning("No data fetched from Google Ads API")

if __name__ == "__main__":
    main()
