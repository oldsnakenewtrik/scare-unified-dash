#!/usr/bin/env python
"""
Script to fix the migrations table in the Railway database.
This script will:
1. Check if the migrations table exists
2. If it exists with wrong schema, drop and recreate it
3. Otherwise, create it if it doesn't exist

Run this directly on Railway using:
railway run python fix_migrations_table.py
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables"""
    # Try to get the DATABASE_URL directly
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        logger.info("Using DATABASE_URL environment variable")
        return database_url
    
    # Or build from individual components
    db_host = os.environ.get('PGHOST', 'localhost')
    db_port = os.environ.get('PGPORT', '5432')
    db_name = os.environ.get('PGDATABASE', 'railway')
    db_user = os.environ.get('PGUSER', 'postgres')
    db_pass = os.environ.get('PGPASSWORD', '')
    
    # Build the connection string
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

def fix_migrations_table():
    """Check migrations table and recreate if needed"""
    try:
        # Connect to the database
        database_url = get_database_url()
        logger.info(f"Connecting to database")
        
        # Create database engine
        engine = create_engine(
            database_url,
            connect_args={
                "connect_timeout": 60,
                "application_name": "SCARE Migration Fix Script",
                "options": "-c statement_timeout=60000",
                "sslmode": "prefer"
            }
        )
        
        # Check if the migrations table exists and has the correct schema
        with engine.connect() as conn:
            # First check if the table exists
            inspector = inspect(engine)
            if "migrations" in inspector.get_table_names():
                logger.info("Migrations table exists, checking schema")
                
                # Check if the required columns exist
                try:
                    # Try to query the table to check schema
                    result = conn.execute(text("SELECT id, name, applied_at FROM migrations LIMIT 1"))
                    logger.info("Migrations table has the correct schema")
                    return True
                except Exception as e:
                    logger.warning(f"Migrations table exists but has wrong schema: {str(e)}")
                    
                    # Drop the table
                    logger.info("Dropping migrations table with incorrect schema")
                    conn.execute(text("DROP TABLE migrations"))
                    conn.commit()
                    logger.info("Migrations table dropped successfully")
            
            # Create the migrations table with the correct schema
            logger.info("Creating migrations table with correct schema")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Migrations table created successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to fix migrations table: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting migrations table fix script")
    success = fix_migrations_table()
    if success:
        logger.info("Migrations table fix completed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix migrations table")
        sys.exit(1)
