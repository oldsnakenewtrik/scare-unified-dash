#!/usr/bin/env python3
"""
Script to check if data is being stored in the database.
This script queries the database to see if Google Ads data is present.
"""

import os
import sys
import logging
import pandas as pd
import sqlalchemy as sa
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('database_check')

# Database URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

def check_database_connection():
    """Check if we can connect to the database."""
    try:
        engine = sa.create_engine(DATABASE_URL)
        conn = engine.connect()
        logger.info("Successfully connected to the database")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return False

def check_tables_exist():
    """Check if the required tables exist in the database."""
    try:
        engine = sa.create_engine(DATABASE_URL)
        conn = engine.connect()
        
        # Check if the fact_google_ads table exists
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'scare_metrics'
                AND table_name = 'fact_google_ads'
            )
        """
        result = conn.execute(sa.text(query)).fetchone()
        
        if result and result[0]:
            logger.info("fact_google_ads table exists")
        else:
            logger.warning("fact_google_ads table does not exist")
        
        # Check if dimension tables exist
        tables = ['dim_campaign', 'dim_date']
        for table in tables:
            query = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'scare_metrics'
                    AND table_name = '{table}'
                )
            """
            result = conn.execute(sa.text(query)).fetchone()
            
            if result and result[0]:
                logger.info(f"{table} table exists")
            else:
                logger.warning(f"{table} table does not exist")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error checking tables: {str(e)}")
        return False

def check_google_ads_data():
    """Check if there's any data in the fact_google_ads table."""
    try:
        engine = sa.create_engine(DATABASE_URL)
        conn = engine.connect()
        
        # Count total records
        query = """
            SELECT COUNT(*) FROM scare_metrics.fact_google_ads
        """
        result = conn.execute(sa.text(query)).fetchone()
        total_records = result[0] if result else 0
        
        logger.info(f"Total records in fact_google_ads: {total_records}")
        
        # Get the most recent data
        if total_records > 0:
            query = """
                SELECT fg.impressions, fg.clicks, fg.cost, fg.date_id, d.full_date, c.campaign_name
                FROM scare_metrics.fact_google_ads fg
                JOIN scare_metrics.dim_date d ON fg.date_id = d.date_id
                JOIN scare_metrics.dim_campaign c ON fg.campaign_id = c.campaign_id
                ORDER BY d.full_date DESC
                LIMIT 5
            """
            
            try:
                results = conn.execute(sa.text(query)).fetchall()
                logger.info(f"Recent Google Ads data ({len(results)} records):")
                
                for row in results:
                    logger.info(f"Campaign: {row.campaign_name}, Date: {row.full_date}, Impressions: {row.impressions}, Clicks: {row.clicks}, Cost: {row.cost}")
            except Exception as e:
                logger.error(f"Error fetching recent data: {str(e)}")
                
                # Try a simpler query without joins in case schema is different
                simple_query = """
                    SELECT impressions, clicks, cost, date_id
                    FROM scare_metrics.fact_google_ads
                    ORDER BY id DESC
                    LIMIT 5
                """
                try:
                    simple_results = conn.execute(sa.text(simple_query)).fetchall()
                    logger.info(f"Basic Google Ads data ({len(simple_results)} records):")
                    
                    for row in simple_results:
                        logger.info(f"Date ID: {row.date_id}, Impressions: {row.impressions}, Clicks: {row.clicks}, Cost: {row.cost}")
                except Exception as e2:
                    logger.error(f"Error with simpler query too: {str(e2)}")
        
        conn.close()
        return total_records > 0
    except Exception as e:
        logger.error(f"Error checking Google Ads data: {str(e)}")
        return False

def check_table_schema():
    """Check the schema of the fact_google_ads table."""
    try:
        engine = sa.create_engine(DATABASE_URL)
        conn = engine.connect()
        
        query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'scare_metrics' AND table_name = 'fact_google_ads'
            ORDER BY ordinal_position
        """
        
        results = conn.execute(sa.text(query)).fetchall()
        
        if results:
            logger.info("fact_google_ads table schema:")
            for column in results:
                logger.info(f"  {column.column_name}: {column.data_type}")
        else:
            logger.warning("Could not retrieve schema for fact_google_ads table")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error checking table schema: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting database check")
    
    if not check_database_connection():
        logger.error("Database connection check failed")
        sys.exit(1)
    
    check_tables_exist()
    check_table_schema()
    has_data = check_google_ads_data()
    
    if has_data:
        logger.info("Database check completed successfully - data is present")
        sys.exit(0)
    else:
        logger.warning("No Google Ads data found in the database")
        sys.exit(1)
