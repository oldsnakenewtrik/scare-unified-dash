#!/usr/bin/env python
"""
Script to apply database migrations to the Railway PostgreSQL database.
This script will apply all migration scripts in the migrations/ directory
that haven't been applied yet.
"""

import os
import sys
import logging
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_url():
    """Get the database URL from environment variables or command line arguments"""
    # Try to load from .env file if it exists
    load_dotenv()
    
    # Get database connection details from environment variables
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        # If not set, try to construct from individual parts
        db_host = os.getenv("PGHOST")
        db_port = os.getenv("PGPORT", "5432")
        db_name = os.getenv("PGDATABASE")
        db_user = os.getenv("PGUSER")
        db_password = os.getenv("PGPASSWORD")
        
        if all([db_host, db_name, db_user, db_password]):
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    return db_url

def get_applied_migrations(conn):
    """Get a list of migrations that have already been applied"""
    # Create migrations table if it doesn't exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS public.migrations (
        id SERIAL PRIMARY KEY,
        migration_name VARCHAR(255) NOT NULL UNIQUE,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    conn.execute(text(create_table_query))
    
    # Get list of applied migrations
    query = "SELECT migration_name FROM public.migrations"
    result = conn.execute(text(query))
    return [row[0] for row in result]

def apply_migration(conn, migration_file, migration_name):
    """Apply a single migration file"""
    try:
        logger.info(f"Applying migration: {migration_name}")
        
        # Read the migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute the migration
        conn.execute(text(migration_sql))
        
        # Record the migration as applied
        insert_query = """
        INSERT INTO public.migrations (migration_name) VALUES (:name)
        """
        conn.execute(text(insert_query), {"name": migration_name})
        
        logger.info(f"Successfully applied migration: {migration_name}")
        return True
    except Exception as e:
        logger.error(f"Error applying migration {migration_name}: {str(e)}")
        return False

def main():
    """Main function to apply migrations"""
    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument("--db-url", help="Database URL (overrides environment variables)")
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or get_db_url()
    
    if not db_url:
        logger.error("Database URL not provided. Set DATABASE_URL environment variable or use --db-url")
        sys.exit(1)
    
    try:
        # Create database engine
        engine = create_engine(db_url)
        
        # Get list of migration files
        migrations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        
        if not migration_files:
            logger.info("No migration files found")
            return
        
        with engine.connect() as conn:
            # Start transaction
            with conn.begin():
                # Get list of applied migrations
                applied_migrations = get_applied_migrations(conn)
                
                # Apply migrations that haven't been applied yet
                for migration_file in migration_files:
                    migration_name = os.path.basename(migration_file)
                    if migration_name not in applied_migrations:
                        migration_path = os.path.join(migrations_dir, migration_file)
                        success = apply_migration(conn, migration_path, migration_name)
                        if not success:
                            logger.error(f"Failed to apply migration: {migration_name}")
                            sys.exit(1)
        
        logger.info("All migrations applied successfully")
    
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
