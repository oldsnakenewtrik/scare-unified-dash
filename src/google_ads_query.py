#!/usr/bin/env python
"""Google Ads API Query Script.

This script queries the Google Ads API to fetch campaign performance metrics,
displays the data structure, and provides SQL for creating appropriate tables.
"""

import os
import sys
from datetime import datetime, timedelta
import yaml
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import pandas as pd
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_google_ads_client():
    """Load Google Ads client from configuration file."""
    try:
        # Path to the Google Ads YAML file
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                "credentials", "google_ads", "google-ads.yaml")
        
        if not os.path.exists(yaml_path):
            logger.error(f"Could not find google-ads.yaml at {yaml_path}")
            yaml_path = input("Please enter the full path to your google-ads.yaml file: ")
        
        with open(yaml_path, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
            
        # Initialize Google Ads client
        google_ads_client = GoogleAdsClient.load_from_dict(config)
        return google_ads_client
    
    except Exception as e:
        logger.error(f"Error loading Google Ads client: {e}")
        return None

def get_campaigns(client, customer_id):
    """Get campaigns for the specified customer."""
    try:
        ga_service = client.get_service("GoogleAdsService")
        
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign_budget.amount_micros,
                campaign.advertising_channel_type,
                campaign.advertising_channel_sub_type
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.id
        """
        
        # Execute the query
        response = ga_service.search(customer_id=customer_id, query=query)
        
        # Print the campaigns
        campaigns = []
        for row in response:
            campaign = {
                "id": row.campaign.id,
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "budget": row.campaign_budget.amount_micros / 1000000,
                "channel_type": row.campaign.advertising_channel_type.name,
                "sub_channel_type": row.campaign.advertising_channel_sub_type.name if row.campaign.advertising_channel_sub_type else None
            }
            campaigns.append(campaign)
        
        return campaigns
    
    except GoogleAdsException as ex:
        logger.error(f"Request with ID '{ex.request_id}' failed with status "
                    f"'{ex.error.code().name}' and includes the following errors:")
        for error in ex.failure.errors:
            logger.error(f"\tError with message '{error.message}'.")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    logger.error(f"\t\tOn field: {field_path_element.field_name}")
        return []

def get_campaign_metrics(client, customer_id, date_range=30):
    """Get metrics for all campaigns."""
    try:
        ga_service = client.get_service("GoogleAdsService")
        
        # Define the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=date_range)
        
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
                metrics.cost_per_conversion,
                segments.date
            FROM campaign
            WHERE 
                campaign.status != 'REMOVED'
                AND segments.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY segments.date DESC
        """
        
        # Execute the query
        response = ga_service.search(customer_id=customer_id, query=query)
        
        # Process the results
        metrics = []
        for row in response:
            metric = {
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "date": row.segments.date,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": row.metrics.cost_micros / 1000000,  # Convert micros to standard currency
                "average_cpc": row.metrics.average_cpc / 1000000,  # Convert micros to standard currency
                "conversions": row.metrics.conversions,
                "conversion_value": row.metrics.conversions_value,
                "cost_per_conversion": row.metrics.cost_per_conversion / 1000000 if row.metrics.conversions > 0 else 0
            }
            metrics.append(metric)
        
        return metrics
    
    except GoogleAdsException as ex:
        logger.error(f"Request with ID '{ex.request_id}' failed with status "
                    f"'{ex.error.code().name}' and includes the following errors:")
        for error in ex.failure.errors:
            logger.error(f"\tError with message '{error.message}'.")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    logger.error(f"\t\tOn field: {field_path_element.field_name}")
        return []

def generate_schema_from_metrics(metrics):
    """Generate SQL schema from metrics data structure."""
    if not metrics:
        return "No metrics data available to generate schema."
    
    # Use the first metrics entry as a sample
    sample = metrics[0]
    
    # Generate SQL for creating the Google Ads fact table
    sql = """
CREATE TABLE IF NOT EXISTS scare_metrics.fact_google_ads (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(12,2) DEFAULT 0,
    average_cpc DECIMAL(12,2) DEFAULT 0,
    conversions DECIMAL(10,2) DEFAULT 0,
    conversion_value DECIMAL(12,2) DEFAULT 0,
    cost_per_conversion DECIMAL(12,2) DEFAULT 0,
    source VARCHAR(50) DEFAULT 'Google Ads',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
    
    # Generate sample insert statement
    insert_sql = """
-- Sample insert statement for the Google Ads fact table
INSERT INTO scare_metrics.fact_google_ads (
    date, campaign_id, campaign_name, impressions, clicks, 
    cost, average_cpc, conversions, conversion_value, cost_per_conversion
) VALUES
"""
    
    # Add a few sample rows based on actual data
    for i, metric in enumerate(metrics[:5]):  # Use first 5 rows as examples
        insert_sql += f"""(
    '{metric['date']}', 
    {metric['campaign_id']}, 
    '{metric['campaign_name'].replace("'", "''")}', 
    {int(metric['impressions'])}, 
    {int(metric['clicks'])}, 
    {metric['cost']}, 
    {metric['average_cpc']}, 
    {metric['conversions']}, 
    {metric['conversion_value']}, 
    {metric['cost_per_conversion']}
)"""
        if i < min(4, len(metrics) - 1):  # Add comma except for last row
            insert_sql += ",\n"
        else:
            insert_sql += ";\n"
    
    return sql + insert_sql

def main():
    """Main function to run the Google Ads API query."""
    logger.info("Loading Google Ads client...")
    client = load_google_ads_client()
    
    if not client:
        logger.error("Failed to load Google Ads client. Exiting.")
        sys.exit(1)
    
    # Get customer ID from config or prompt
    try:
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                "credentials", "google_ads", "google-ads.yaml")
        with open(yaml_path, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
        customer_id = config.get("customer_id", None)
    except Exception:
        customer_id = None
    
    if not customer_id:
        customer_id = input("Please enter your Google Ads customer ID (without hyphens): ")
    
    # Get campaigns
    logger.info(f"Fetching campaigns for customer ID: {customer_id}")
    campaigns = get_campaigns(client, customer_id)
    
    if not campaigns:
        logger.warning("No campaigns found or an error occurred.")
    else:
        logger.info(f"Found {len(campaigns)} campaigns.")
        # Display campaigns in a table format
        df_campaigns = pd.DataFrame(campaigns)
        print("\n=== Google Ads Campaigns ===")
        print(df_campaigns.to_string())
        
        # Save campaigns to JSON for reference
        with open("google_ads_campaigns.json", "w") as f:
            json.dump(campaigns, f, indent=2)
        logger.info("Saved campaigns to google_ads_campaigns.json")
    
    # Get campaign metrics
    logger.info("Fetching campaign metrics for the last 30 days...")
    metrics = get_campaign_metrics(client, customer_id, date_range=30)
    
    if not metrics:
        logger.warning("No metrics found or an error occurred.")
    else:
        logger.info(f"Found metrics for {len(metrics)} campaign-days.")
        
        # Display metrics in a table format (limited sample)
        df_metrics = pd.DataFrame(metrics[:10])  # Show first 10 rows
        print("\n=== Google Ads Metrics (Sample) ===")
        print(df_metrics.to_string())
        
        # Save metrics to JSON for reference
        with open("google_ads_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info("Saved metrics to google_ads_metrics.json")
        
        # Generate and display schema
        schema_sql = generate_schema_from_metrics(metrics)
        print("\n=== Generated SQL Schema for Google Ads ===")
        print(schema_sql)
        
        # Save schema to file
        with open("google_ads_schema.sql", "w") as f:
            f.write(schema_sql)
        logger.info("Saved schema SQL to google_ads_schema.sql")

if __name__ == "__main__":
    main()
