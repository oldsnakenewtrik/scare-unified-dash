"""
Setup script for local development with Railway PostgreSQL
This script will help you set up the correct environment variables for local development
"""
import os
import sys
import subprocess
import re

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")

def run_command(command):
    """Run a command and return its output"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        print(e.stderr)
        return None

def check_railway_cli():
    """Check if Railway CLI is installed and the user is logged in"""
    print_header("Checking Railway CLI")
    
    # Check if Railway CLI is installed
    version = run_command("railway --version")
    if not version:
        print_error("Railway CLI is not installed or not in PATH")
        print_info("Please install Railway CLI: https://docs.railway.app/develop/cli")
        return False
    
    print_success(f"Railway CLI is installed: {version}")
    
    # Check if the user is logged in
    status = run_command("railway status")
    if not status or "not logged in" in status.lower():
        print_error("You are not logged in to Railway")
        print_info("Please run 'railway login' to log in")
        return False
    
    print_success("You are logged in to Railway")
    
    # Check if a project is linked
    if "project:" not in status.lower():
        print_warning("No Railway project is linked")
        print_info("Please run 'railway link' to link your project")
        return False
    
    project_match = re.search(r"Project: (.+)", status)
    if project_match:
        project_name = project_match.group(1)
        print_success(f"Project linked: {project_name}")
    
    return True

def create_local_env_file():
    """Create a .env.local file with the correct environment variables"""
    print_header("Creating local environment file")
    
    # Check if .env.local already exists
    if os.path.exists(".env.local"):
        print_warning(".env.local file already exists")
        overwrite = input("Do you want to overwrite it? (y/n): ").lower()
        if overwrite != 'y':
            print_info("Skipping .env.local creation")
            return
    
    # Get the external PostgreSQL connection string from Railway
    print_info("Getting PostgreSQL connection details from Railway...")
    
    # Try to get the service name for PostgreSQL
    services = run_command("railway service")
    if not services:
        print_error("Could not get Railway services")
        return
    
    # Look for PostgreSQL service
    postgres_service = None
    for line in services.splitlines():
        if "postgres" in line.lower():
            postgres_service = line.strip()
            break
    
    if not postgres_service:
        print_warning("Could not find PostgreSQL service in Railway")
        print_info("You'll need to get the external connection string manually from the Railway dashboard")
        
        # Ask the user to input the connection string
        db_url = input("Please enter the external PostgreSQL connection string from Railway dashboard: ")
        if not db_url:
            print_error("No connection string provided")
            return
    else:
        print_success(f"Found PostgreSQL service: {postgres_service}")
        
        # Get the connection string using Railway variables
        # Note: This might not work depending on how Railway CLI works
        print_warning("Unfortunately, Railway CLI doesn't provide a direct way to get the external connection string")
        print_info("Please get the external connection string from the Railway dashboard")
        
        # Ask the user to input the connection string
        db_url = input("Please enter the external PostgreSQL connection string from Railway dashboard: ")
        if not db_url:
            print_error("No connection string provided")
            return
    
    # Create the .env.local file
    with open(".env.local", "w") as f:
        f.write("# Local development environment variables\n")
        f.write(f"DATABASE_URL={db_url}\n")
        f.write("# Add any other required environment variables below\n")
    
    print_success(".env.local file created successfully")
    print_info("You can now use this file for local development")

def check_database_connection():
    """Check if we can connect to the database"""
    print_header("Testing database connection")
    
    # Run the database connection test script
    print_info("Running database connection test...")
    result = run_command("python test_db_connection.py")
    
    if not result:
        print_error("Database connection test failed")
        return False
    
    if "Connection successful" in result:
        print_success("Database connection test successful")
        return True
    else:
        print_error("Database connection test failed")
        print_info("Please check your connection string and ensure the database is accessible")
        return False

def main():
    """Main function"""
    print_header("Railway Local Development Setup")
    
    # Check Railway CLI
    if not check_railway_cli():
        return
    
    # Create local environment file
    create_local_env_file()
    
    # Check database connection
    check_database_connection()
    
    print_header("Next Steps")
    print_info("1. Make sure you have the correct DATABASE_URL in your .env.local file")
    print_info("2. Run your application with: python -m uvicorn src.api.main:app --reload")
    print_info("3. If you still have issues, check the Railway dashboard for more information")

if __name__ == "__main__":
    main()
