#!/usr/bin/env python

import os
import sys
import logging
import json
import pandas as pd
import sqlalchemy as sa
from datetime import datetime
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('google_ads_import')

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

def get_campaign_dimension_id(conn, campaign_name, source_campaign_id=None):
    """
    Get or create a campaign dimension ID.
    
    Args:
        conn: Database connection
        campaign_name (str): Name of the campaign
        source_campaign_id (str, optional): Original campaign ID from the source system
        
    Returns:
        int: Campaign dimension ID
    """
    try:
        # Check if campaign already exists
        query = sa.text("""
            SELECT id 
            FROM scare_metrics.dim_campaign 
            WHERE source_campaign_id = :source_campaign_id 
            AND source = 'Google Ads'
        """)
        
        result = conn.execute(query, {"source_campaign_id": source_campaign_id}).fetchone()
        
        if result:
            # Campaign exists, return the ID
            return result[0]
            
        # Campaign doesn't exist, create it
        insert_query = sa.text("""
            INSERT INTO scare_metrics.dim_campaign (
                campaign_name, 
                source, 
                source_campaign_id,
                created_at,
                updated_at
            ) VALUES (
                :campaign_name, 
                'Google Ads', 
                :source_campaign_id,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            ) RETURNING id
        """)
        
        result = conn.execute(
            insert_query, 
            {
                "campaign_name": campaign_name, 
                "source_campaign_id": source_campaign_id
            }
        ).fetchone()
        
        return result[0]
        
    except Exception as e:
        logger.error(f"Error getting campaign dimension ID: {str(e)}")
        raise

def get_date_dimension_id(conn, date_str):
    """
    Get or create a date dimension ID.
    
    Args:
        conn: Database connection
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        int: Date dimension ID
    """
    try:
        # Parse the date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Check if date already exists
        query = sa.text("""
            SELECT id 
            FROM scare_metrics.dim_date 
            WHERE full_date = :full_date
        """)
        
        result = conn.execute(query, {"full_date": date_str}).fetchone()
        
        if result:
            # Date exists, return the ID
            return result[0]
            
        # Date doesn't exist, create it
        month_name = date_obj.strftime("%B")
        day_of_week = date_obj.strftime("%A")
        
        insert_query = sa.text("""
            INSERT INTO scare_metrics.dim_date (
                full_date,
                year,
                month,
                month_name,
                day_of_month,
                day_of_week,
                day_of_week_name,
                quarter,
                created_at,
                updated_at
            ) VALUES (
                :full_date,
                :year,
                :month,
                :month_name,
                :day_of_month,
                :day_of_week,
                :day_of_week_name,
                :quarter,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            ) RETURNING id
        """)
        
        # Calculate quarter
        quarter = (date_obj.month - 1) // 3 + 1
        
        result = conn.execute(
            insert_query, 
            {
                "full_date": date_str,
                "year": date_obj.year,
                "month": date_obj.month,
                "month_name": month_name,
                "day_of_month": date_obj.day,
                "day_of_week": date_obj.weekday() + 1,  # 1-7 (Monday is 1)
                "day_of_week_name": day_of_week,
                "quarter": quarter
            }
        ).fetchone()
        
        return result[0]
        
    except Exception as e:
        logger.error(f"Error getting date dimension ID: {str(e)}")
        raise

def import_google_ads_data(json_file_path):
    """
    Import Google Ads data from JSON file to database.
    
    Args:
        json_file_path (str): Path to JSON file containing Google Ads data
        
    Returns:
        int: Number of records inserted
    """
    try:
        # Read JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)
            
        logger.info(f"Loaded {len(data)} records from {json_file_path}")
        
        # Create engine and connection
        engine = sa.create_engine(DATABASE_URL)
        
        records_inserted = 0
        
        with engine.begin() as conn:
            # Process each record
            for item in data:
                # Get dimension IDs
                campaign_id = get_campaign_dimension_id(
                    conn,
                    item['campaign_name'],
                    str(item['campaign_id'])
                )
                
                date_id = get_date_dimension_id(conn, item['date'])
                
                # Calculate CTR (Click-Through Rate) if not provided
                if 'ctr' not in item and item['impressions'] > 0:
                    ctr = (item['clicks'] / item['impressions']) * 100
                else:
                    ctr = item.get('ctr', 0)
                
                # Get average CPC from the item or calculate it
                if 'average_cpc' not in item and item['clicks'] > 0:
                    avg_cpc = item['cost'] / item['clicks']
                else:
                    avg_cpc = item.get('average_cpc', 0)
                
                # Check if record already exists
                check_query = sa.text("""
                    SELECT id
                    FROM scare_metrics.fact_google_ads
                    WHERE campaign_id = :campaign_id
                    AND date_id = :date_id
                """)
                
                existing = conn.execute(
                    check_query,
                    {"campaign_id": campaign_id, "date_id": date_id}
                ).fetchone()
                
                if existing:
                    # Update existing record
                    update_query = sa.text("""
                        UPDATE scare_metrics.fact_google_ads
                        SET 
                            impressions = :impressions,
                            clicks = :clicks,
                            cost = :cost,
                            average_cpc = :average_cpc,
                            ctr = :ctr,
                            conversions = :conversions,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE campaign_id = :campaign_id
                        AND date_id = :date_id
                    """)
                    
                    conn.execute(
                        update_query,
                        {
                            "campaign_id": campaign_id,
                            "date_id": date_id,
                            "impressions": item['impressions'],
                            "clicks": item['clicks'],
                            "cost": item['cost'],
                            "average_cpc": avg_cpc,
                            "ctr": ctr,
                            "conversions": item.get('conversions', 0)
                        }
                    )
                else:
                    # Insert new record
                    insert_query = sa.text("""
                        INSERT INTO scare_metrics.fact_google_ads (
                            campaign_id,
                            date_id,
                            impressions,
                            clicks,
                            cost,
                            average_cpc,
                            ctr,
                            conversions,
                            created_at,
                            updated_at
                        ) VALUES (
                            :campaign_id,
                            :date_id,
                            :impressions,
                            :clicks,
                            :cost,
                            :average_cpc,
                            :ctr,
                            :conversions,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                    """)
                    
                    conn.execute(
                        insert_query,
                        {
                            "campaign_id": campaign_id,
                            "date_id": date_id,
                            "impressions": item['impressions'],
                            "clicks": item['clicks'],
                            "cost": item['cost'],
                            "average_cpc": avg_cpc,
                            "ctr": ctr,
                            "conversions": item.get('conversions', 0)
                        }
                    )
                
                records_inserted += 1
                
                # Log progress for large datasets
                if records_inserted % 100 == 0:
                    logger.info(f"Processed {records_inserted} records so far")
            
        logger.info(f"Successfully imported {records_inserted} records into the database")
        return records_inserted
        
    except Exception as e:
        logger.error(f"Error importing Google Ads data: {str(e)}")
        return 0

def main():
    """Main function"""
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
    else:
        json_file_path = 'google_ads_data.json'
    
    if not os.path.exists(json_file_path):
        logger.error(f"JSON file not found: {json_file_path}")
        sys.exit(1)
    
    records_inserted = import_google_ads_data(json_file_path)
    logger.info(f"Import completed. {records_inserted} records processed.")

if __name__ == "__main__":
    main()
