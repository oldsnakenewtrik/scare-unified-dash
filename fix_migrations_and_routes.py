#!/usr/bin/env python3
"""
Script to fix migrations table and verify API routes are registered
This addresses the two key issues:
1. Missing 'name' column in migrations table
2. API routes not being properly registered
"""
import os
import sys
import psycopg2
import requests
from dotenv import load_dotenv

# Load environment variables if .env file exists
load_dotenv(verbose=True)

def get_database_url():
    """Get database URL from environment with Railway priorities"""
    # Check if we're in Railway
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT")
    
    # First try internal networking if in Railway
    if railway_env:
        if os.environ.get("DATABASE_URL"):
            return os.environ.get("DATABASE_URL")
        
        # Build URL from components
        host = os.environ.get("PGHOST") or "postgres"
        port = os.environ.get("PGPORT") or "5432"
        user = os.environ.get("PGUSER") or os.environ.get("POSTGRES_USER") or "postgres"
        password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD") or ""
        db = os.environ.get("PGDATABASE") or os.environ.get("POSTGRES_DB") or "railway"
        
        # Build internal URL for Railway
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    # For local development
    return os.environ.get("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/postgres"

def fix_migrations_table():
    """Fix the migrations table by recreating it with the proper schema"""
    print("Fixing migrations table...")
    
    # Get database URL
    db_url = get_database_url()
    print(f"Using database URL: {db_url.replace(db_url.split('@')[0], '***:***')}")  # Mask credentials
    
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if migrations table exists
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'migrations')")
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            # Check if name column exists
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'migrations' AND column_name = 'name')")
            name_column_exists = cursor.fetchone()[0]
            
            if name_column_exists:
                print("Migrations table already has 'name' column. No fix needed.")
                return
            
            print("Migrations table exists but doesn't have 'name' column. Recreating table...")
        else:
            print("Migrations table doesn't exist. Creating it...")
        
        # SQL to fix migrations table
        fix_sql = """
        DROP TABLE IF EXISTS migrations;
        
        CREATE TABLE migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Insert records for migrations that have already been applied
        INSERT INTO migrations (name) VALUES 
        ('001_create_sm_fact_bing_ads'),
        ('002_create_sm_fact_google_ads'),
        ('003_create_campaign_mappings'),
        ('004_create_campaign_hierarchy'),
        ('005_add_network_to_bing_ads');
        """
        
        cursor.execute(fix_sql)
        print("Migrations table fixed successfully!")
        
    except Exception as e:
        print(f"Error fixing migrations table: {str(e)}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def check_api_routes():
    """Check if API routes are registered by accessing status endpoint"""
    print("\nChecking API routes...")
    
    # Get API base URL from environment
    api_url = os.environ.get("API_URL") or "http://localhost:8000"
    
    # Try accessing our health check endpoint
    health_url = f"{api_url}/api/health"
    debug_url = f"{api_url}/api/debug-routes"
    
    try:
        print(f"Testing health endpoint: {health_url}")
        response = requests.get(health_url, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Health endpoint accessible!")
            print(f"Response: {response.json()}")
        else:
            print(f"Health endpoint returned non-200 status: {response.status_code}")
            print(f"Response: {response.text}")
            
        # Try debug routes endpoint
        print(f"\nTesting debug routes endpoint: {debug_url}")
        response = requests.get(debug_url, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Debug routes endpoint accessible!")
            print(f"Registered routes: {response.json()}")
        else:
            print(f"Debug routes endpoint returned non-200 status: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error accessing API endpoints: {str(e)}")

if __name__ == "__main__":
    print("Starting fix script for migrations and API routes...")
    fix_migrations_table()
    
    # Only check API routes if not in Railway environment (can't make HTTP requests from within)
    if not os.environ.get("RAILWAY_ENVIRONMENT"):
        check_api_routes()
    else:
        print("\nRunning in Railway environment - skipping API route check.")
        print("Please check the routes manually by visiting:")
        print("- Health endpoint: https://your-app-url.railway.app/api/health")
        print("- Debug routes endpoint: https://your-app-url.railway.app/api/debug-routes")
    
    print("\nScript completed!")
