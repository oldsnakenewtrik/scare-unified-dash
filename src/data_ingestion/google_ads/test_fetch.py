import os
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import logging
import pandas as pd
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('google_ads_test')

# Load environment variables
load_dotenv()

def get_google_ads_client():
    """Create and return a Google Ads API client."""
    try:
        # Load credentials from environment
        credentials = {
            "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
            "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
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

def fetch_campaign_data(days_back=30):
    """Fetch campaign performance data for the last X days."""
    client = get_google_ads_client()
    if not client:
        logger.error("Failed to create Google Ads client")
        return
    
    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
    
    # Calculate date range
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=days_back)
    
    # Format dates as strings
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    logger.info(f"Fetching campaign data from {start_date_str} to {end_date_str}")
    
    try:
        ga_service = client.get_service("GoogleAdsService")
        
        # Query to fetch basic campaign metrics
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
            WHERE segments.date BETWEEN '{start_date_str}' AND '{end_date_str}'
            ORDER BY segments.date DESC
            LIMIT 100
        """
        
        # Execute the query
        response = ga_service.search_stream(customer_id=customer_id, query=query)
        
        # Process the results
        results = []
        for batch in response:
            for row in batch.results:
                results.append({
                    "date": row.segments.date,
                    "campaign_id": row.campaign.id,
                    "campaign_name": row.campaign.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": row.metrics.cost_micros / 1_000_000,
                    "conversions": row.metrics.conversions
                })
        
        # Convert to DataFrame for easier viewing
        if results:
            df = pd.DataFrame(results)
            logger.info(f"Found {len(results)} campaign data rows")
            logger.info("\nSample campaign data (first 5 rows):")
            print(df.head(5).to_string())
            
            # Summary statistics
            logger.info("\nSummary by campaign:")
            summary = df.groupby("campaign_name").agg({
                "impressions": "sum",
                "clicks": "sum",
                "cost": "sum",
                "conversions": "sum"
            }).reset_index()
            print(summary.to_string())
            
            # Save to CSV
            csv_file = "campaign_data_sample.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"Data saved to {csv_file}")
        else:
            logger.info("No campaign data found for the specified date range")
    
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex.error.code().name}")
        for error in ex.failure.errors:
            logger.error(f"  - Error message: {error.message}")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    logger.error(f"    - On field: {field_path_element.field_name}")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    fetch_campaign_data(days_back=90)  # Fetch data for the last 90 days
