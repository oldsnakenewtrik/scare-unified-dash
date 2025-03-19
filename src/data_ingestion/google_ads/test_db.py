#!/usr/bin/env python

import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("db_test")

def main():
    """Test database connection and schema."""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@localhost:5432/scare_metrics")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return
    
    logger.info(f"Testing connection to database: {db_url}")
    
    try:
        # Create engine and connect
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Test connection by executing a simple query
            result = conn.execute(text("SELECT 1")).fetchone()
            if result:
                logger.info("Successfully connected to the database")
            
            # Check if the required schema exists
            schema_result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'scare_metrics'
            """)).fetchone()
            
            if schema_result:
                logger.info("Found 'scare_metrics' schema")
            else:
                logger.warning("Schema 'scare_metrics' not found")
            
            # List tables in the schema
            if schema_result:
                tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'scare_metrics'
                """)).fetchall()
                
                logger.info(f"Found {len(tables)} tables in 'scare_metrics' schema:")
                for table in tables:
                    logger.info(f"  - {table[0]}")
        
        logger.info("Database connection test completed successfully")
        
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")

if __name__ == "__main__":
    main()
