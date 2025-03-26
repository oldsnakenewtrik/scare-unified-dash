#!/usr/bin/env python
"""
Railway Local Development Helper Script

This script helps with local development using the Railway CLI.
It provides commands for common tasks like running the API server,
triggering the ETL process, and checking the database.
"""

import os
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path

def run_command(command, capture_output=True):
    """Run a command and return the result"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=capture_output, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(f"Error: {result.stderr}")
        return False, result.stderr
    return True, result.stdout

def check_railway_cli():
    """Check if Railway CLI is installed and logged in"""
    success, output = run_command("railway --version")
    if not success:
        print("Railway CLI is not installed. Please install it first:")
        print("curl -fsSL https://railway.app/install.sh | sh")
        return False
    
    print(f"Railway CLI version: {output.strip()}")
    
    # Check if logged in
    success, output = run_command("railway whoami")
    if not success or "not logged in" in output.lower():
        print("You are not logged in to Railway. Please login first:")
        print("railway login")
        return False
    
    print(f"Logged in as: {output.strip()}")
    return True

def link_project():
    """Link to the Railway project"""
    project_id = "d103846e-ee3c-4c6c-906d-952780be754c"
    success, output = run_command(f"railway link -p {project_id}")
    if not success:
        print(f"Failed to link to project: {project_id}")
        return False
    
    print("Successfully linked to Railway project")
    return True

def run_api_server():
    """Run the API server using Railway environment"""
    print("Starting API server with Railway environment...")
    subprocess.run("railway run python src/api/main.py", shell=True)

def run_etl_once():
    """Run the Google Ads ETL process once"""
    print("Running Google Ads ETL process once...")
    success, output = run_command("railway run python src/data_ingestion/google_ads/main.py --run-once")
    if success:
        print("ETL process completed successfully")
    return success

def check_database():
    """Check database connectivity and tables"""
    print("Checking database connectivity...")
    
    # Check connectivity
    success, output = run_command("""
    railway run python -c "
    import sqlalchemy
    import os
    import pandas as pd
    
    # Get database connection details
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('RAILWAY_DATABASE_URL')
    if not db_url:
        host = os.environ.get('PGHOST', 'localhost')
        port = os.environ.get('PGPORT', '5432')
        user = os.environ.get('PGUSER', 'postgres')
        password = os.environ.get('PGPASSWORD', '')
        dbname = os.environ.get('PGDATABASE', 'postgres')
        db_url = f'postgresql://{user}:{password}@{host}:{port}/{dbname}'
    
    print(f'Connecting to database: {db_url.split('@')[1] if '@' in db_url else db_url}')
    
    # Create engine and connect
    engine = sqlalchemy.create_engine(db_url)
    with engine.connect() as conn:
        # Check if tables exist
        result = conn.execute(sqlalchemy.text('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        '''))
        tables = [row[0] for row in result]
        print('\\nTables in database:')
        for table in sorted(tables):
            print(f'- {table}')
        
        # Check row counts for key tables
        print('\\nRow counts:')
        for table in ['sm_fact_google_ads', 'sm_fact_bing_ads', 'sm_campaign_name_mapping']:
            if table in tables:
                count = conn.execute(sqlalchemy.text(f'SELECT COUNT(*) FROM {table}')).scalar()
                print(f'- {table}: {count} rows')
            else:
                print(f'- {table}: Table does not exist')
    "
    """)
    
    if success:
        print("Database check completed successfully")
    return success

def check_health():
    """Check the health of the API"""
    print("Checking API health...")
    
    # First check if the API is running
    success, output = run_command("curl -s http://localhost:8000/health")
    if not success:
        print("API is not running or health endpoint is not accessible")
        return False
    
    try:
        health_data = json.loads(output)
        print(f"API health status: {health_data.get('status', 'unknown')}")
        
        # Print component statuses
        components = health_data.get('components', {})
        for component_name, component_data in components.items():
            status = component_data.get('status', 'unknown')
            print(f"- {component_name}: {status}")
            if status != 'healthy' and component_data.get('error'):
                print(f"  Error: {component_data.get('error')}")
        
        return health_data.get('status') == 'healthy'
    except json.JSONDecodeError:
        print("Failed to parse health check response")
        print(f"Response: {output}")
        return False

def check_unmapped_campaigns():
    """Check for unmapped campaigns"""
    print("Checking for unmapped campaigns...")
    
    success, output = run_command("curl -s http://localhost:8000/api/unmapped-campaigns")
    if not success:
        print("Failed to check unmapped campaigns")
        return False
    
    try:
        campaigns = json.loads(output)
        print(f"Found {len(campaigns)} unmapped campaigns")
        
        # Group by source system
        by_source = {}
        for campaign in campaigns:
            source = campaign.get('source_system', 'unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(campaign)
        
        # Print summary by source
        for source, campaigns in by_source.items():
            print(f"- {source}: {len(campaigns)} campaigns")
        
        return True
    except json.JSONDecodeError:
        print("Failed to parse unmapped campaigns response")
        print(f"Response: {output}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Railway Local Development Helper')
    parser.add_argument('command', choices=[
        'setup', 'api', 'etl', 'db', 'health', 'unmapped', 'all'
    ], help='Command to run')
    
    args = parser.parse_args()
    
    # Check Railway CLI first
    if not check_railway_cli():
        return 1
    
    # For all commands except setup, make sure we're linked to the project
    if args.command != 'setup':
        if not link_project():
            return 1
    
    # Run the requested command
    if args.command == 'setup':
        print("Setting up Railway CLI for local development...")
        if not link_project():
            return 1
        print("Setup completed successfully")
    
    elif args.command == 'api':
        run_api_server()
    
    elif args.command == 'etl':
        run_etl_once()
    
    elif args.command == 'db':
        check_database()
    
    elif args.command == 'health':
        check_health()
    
    elif args.command == 'unmapped':
        check_unmapped_campaigns()
    
    elif args.command == 'all':
        print("Running all checks...")
        check_database()
        print("\n" + "="*50 + "\n")
        
        # Start API in background
        api_process = subprocess.Popen("railway run python src/api/main.py", shell=True)
        try:
            print("Waiting for API to start...")
            time.sleep(5)  # Give API time to start
            
            # Run health check
            check_health()
            print("\n" + "="*50 + "\n")
            
            # Check unmapped campaigns
            check_unmapped_campaigns()
            print("\n" + "="*50 + "\n")
            
            # Run ETL process
            run_etl_once()
            
            # Wait for user to press Enter
            input("\nPress Enter to stop the API server and exit...")
        finally:
            # Kill the API process
            api_process.terminate()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
