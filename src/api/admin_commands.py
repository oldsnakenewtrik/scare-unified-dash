"""
Admin commands for SCARE Unified Dashboard
- Add to handle tasks that need privileged access to the database
"""
import logging
import os
import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from db_init import get_db_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_google_ads_mappings(db: Session):
    """Clear all Google Ads campaign mappings to force them to appear as unmapped"""
    try:
        # Check existing mappings
        count_query = text("""
            SELECT COUNT(*) FROM sm_campaign_name_mapping
            WHERE source_system = 'Google Ads'
        """)
        count = db.execute(count_query).scalar() or 0
        logger.info(f"Found {count} existing Google Ads mappings")
        
        if count == 0:
            logger.info("No Google Ads mappings to clear")
            return True
        
        # Delete the mappings
        delete_query = text("""
            DELETE FROM sm_campaign_name_mapping
            WHERE source_system = 'Google Ads'
        """)
        
        result = db.execute(delete_query)
        db.commit()
        logger.info(f"Deleted {result.rowcount} Google Ads mappings")
        
        # Verify
        verify_count = db.execute(count_query).scalar() or 0
        logger.info(f"Remaining Google Ads mappings: {verify_count}")
        
        return True
    except Exception as e:
        logger.error(f"Error clearing Google Ads mappings: {str(e)}")
        db.rollback()
        return False

def import_real_google_ads_data(db: Session, file_path=None):
    """Import real Google Ads data from JSON file or sample data for testing"""
    try:
        # Use sample data if no file path provided
        if not file_path:
            # Create sample data based on real campaign naming patterns
            data = [
                {
                    "date": "2025-03-10",
                    "campaign_id": "17345786789",
                    "campaign_name": "Mattress - Search - Brand - ENG",
                    "impressions": 1200,
                    "clicks": 65,
                    "cost": 120.50,
                    "conversions": 8
                },
                {
                    "date": "2025-03-10",
                    "campaign_id": "22345786790",
                    "campaign_name": "Mattress - Search - Generic - ENG",
                    "impressions": 4500,
                    "clicks": 125,
                    "cost": 350.75,
                    "conversions": 3
                },
                {
                    "date": "2025-03-10",
                    "campaign_id": "32345786791",
                    "campaign_name": "Bed Frame - Search - Brand - ENG",
                    "impressions": 800,
                    "clicks": 45,
                    "cost": 80.25,
                    "conversions": 4
                },
                {
                    "date": "2025-03-10",
                    "campaign_id": "42345786792",
                    "campaign_name": "Bed Frame - Search - Generic - ENG",
                    "impressions": 3200,
                    "clicks": 85,
                    "cost": 250.60,
                    "conversions": 2
                },
                {
                    "date": "2025-03-10",
                    "campaign_id": "52345786793",
                    "campaign_name": "Adjustable Base - Search - Brand - ENG",
                    "impressions": 600,
                    "clicks": 30,
                    "cost": 60.40,
                    "conversions": 2
                }
            ]
            logger.info(f"Using sample data with {len(data)} records")
        else:
            # Load data from file
            with open(file_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} records from {file_path}")
        
        # First clear existing Google Ads data
        clear_query = text("DELETE FROM sm_fact_google_ads")
        db.execute(clear_query)
        logger.info("Cleared existing Google Ads data")
        
        # Insert new data
        inserted = 0
        for item in data:
            insert_query = text("""
            INSERT INTO sm_fact_google_ads
                (date, campaign_id, campaign_name, impressions, clicks, cost, conversions)
            VALUES
                (:date, :campaign_id, :campaign_name, :impressions, :clicks, :cost, :conversions)
            """)
            
            db.execute(insert_query, {
                "date": item.get("date"),
                "campaign_id": str(item.get("campaign_id")),
                "campaign_name": item.get("campaign_name"),
                "impressions": item.get("impressions", 0),
                "clicks": item.get("clicks", 0),
                "cost": item.get("cost", 0),
                "conversions": item.get("conversions", 0)
            })
            
            inserted += 1
        
        # Commit the changes
        db.commit()
        logger.info(f"Inserted {inserted} Google Ads records")
        
        # Verify unique campaigns
        verify_query = text("""
        SELECT COUNT(DISTINCT campaign_id) FROM sm_fact_google_ads
        """)
        unique_count = db.execute(verify_query).scalar() or 0
        logger.info(f"Unique Google Ads campaigns in database: {unique_count}")
        
        # Show examples
        examples_query = text("""
        SELECT DISTINCT campaign_id, campaign_name FROM sm_fact_google_ads
        LIMIT 5
        """)
        examples = db.execute(examples_query).fetchall()
        for i, ex in enumerate(examples):
            logger.info(f"Example {i+1}: {ex._mapping['campaign_id']} - {ex._mapping['campaign_name']}")
        
        return True
    except Exception as e:
        logger.error(f"Error importing Google Ads data: {str(e)}")
        db.rollback()
        return False

def run_admin_command(command: str, file_path=None):
    """Run an admin command"""
    try:
        # Get database connection
        engine = get_db_engine()
        with Session(engine) as db:
            if command == "clear_google_ads_mappings":
                return clear_google_ads_mappings(db)
            elif command == "import_real_google_ads_data":
                return import_real_google_ads_data(db, file_path)
            else:
                logger.error(f"Unknown command: {command}")
                return False
    except Exception as e:
        logger.error(f"Error running admin command {command}: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python admin_commands.py <command> [file_path]")
        print("Available commands:")
        print("  clear_google_ads_mappings")
        print("  import_real_google_ads_data [file_path]")
        sys.exit(1)
    
    command = sys.argv[1]
    file_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = run_admin_command(command, file_path)
    
    if success:
        print(f"Command {command} executed successfully!")
        sys.exit(0)
    else:
        print(f"Command {command} failed!")
        sys.exit(1)
