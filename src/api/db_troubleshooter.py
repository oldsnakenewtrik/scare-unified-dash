"""
Database Troubleshooting Tool for Railway Deployments

This script provides comprehensive diagnostics and troubleshooting for database 
connection issues in Railway-hosted applications. It validates database credentials,
tests connectivity, and provides detailed error information.

Usage:
    python db_troubleshooter.py [--fix] [--retry N] [--verbose]

Options:
    --fix       Attempt to fix common issues automatically
    --retry N   Number of retry attempts for connection (default: 5)
    --verbose   Enable verbose logging
"""
import os
import sys
import time
import json
import socket
import logging
import argparse
import traceback
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("psycopg2 not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Environment variables must be set manually.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_troubleshooter")

# Constants
DEFAULT_RETRY_COUNT = 5
DEFAULT_RETRY_DELAY = 5
DEFAULT_TIMEOUT = 10
REQUIRED_TABLES = [
    "sm_fact_google_ads", 
    "sm_fact_bing_ads", 
    "sm_fact_facebook_ads", 
    "sm_fact_linkedin_ads",
    "sm_dim_campaign_mapping"
]

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Database Troubleshooting Tool for Railway Deployments")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common issues automatically")
    parser.add_argument("--retry", type=int, default=DEFAULT_RETRY_COUNT, help=f"Number of retry attempts (default: {DEFAULT_RETRY_COUNT})")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()

def setup_logging(verbose: bool):
    """Configure logging based on verbosity"""
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    # Add a file handler if we're in a writable environment
    try:
        file_handler = logging.FileHandler("db_troubleshoot.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        logger.info("Logging to db_troubleshoot.log")
    except (PermissionError, IOError):
        logger.info("Unable to create log file, logging to console only")

def mask_sensitive_data(data: str) -> str:
    """Mask sensitive data like passwords for logging"""
    if not data:
        return data
    
    if isinstance(data, str) and "://" in data:
        # Mask password in URL
        try:
            parts = data.split("://")
            if "@" in parts[1]:
                userpass, hostdb = parts[1].split("@", 1)
                if ":" in userpass:
                    user, password = userpass.split(":", 1)
                    return f"{parts[0]}://{user}:****@{hostdb}"
        except Exception:
            pass
    
    return data

def log_environment_variables():
    """Log relevant environment variables for debugging"""
    logger.info("Checking environment variables...")
    
    # List of environment variables to check
    db_env_vars = [
        "DATABASE_URL",
        "PGHOST",
        "PGUSER",
        "PGDATABASE",
        "PGPORT",
        "RAILWAY_PUBLIC_DOMAIN",
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_SERVICE_NAME",
        "PORT",
        "Value"  # Sometimes Railway uses this for DATABASE_URL
    ]
    
    # Log environment variables (masking sensitive data)
    env_status = {}
    for var in db_env_vars:
        value = os.environ.get(var)
        if var in ["DATABASE_URL", "PGPASSWORD", "Value"]:
            status = "[SET]" if value else "[NOT SET]"
            logger.info(f"{var}: {status}")
            env_status[var] = status
        else:
            logger.info(f"{var}: {value if value else '[NOT SET]'}")
            env_status[var] = value if value else "[NOT SET]"
    
    return env_status

def get_database_url() -> Optional[str]:
    """Get database URL from environment variables"""
    # Try to get the database URL from the environment
    database_url = os.environ.get("DATABASE_URL")
    
    # If not found, try to construct it from individual components
    if not database_url:
        logger.warning("DATABASE_URL not found in environment variables")
        
        # Try to get individual components
        host = os.environ.get("PGHOST")
        user = os.environ.get("PGUSER")
        password = os.environ.get("PGPASSWORD")
        database = os.environ.get("PGDATABASE")
        port = os.environ.get("PGPORT", "5432")
        
        # Check if we have all required components
        if host and user and password and database:
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            logger.info("Constructed database URL from individual components")
        else:
            # Check if we have a Value environment variable (sometimes used in Railway)
            value = os.environ.get("Value")
            if value and value.startswith("postgresql://"):
                database_url = value
                logger.info("Using database URL from 'Value' environment variable")
            else:
                logger.error("Could not construct database URL from environment variables")
                return None
    
    # Log masked URL for debugging
    masked_url = mask_sensitive_data(database_url)
    logger.info(f"Using database URL: {masked_url}")
    
    return database_url

def parse_database_url(url: str) -> Dict[str, Any]:
    """Parse a database URL into its components"""
    if not url:
        return {}
    
    try:
        parsed = urllib.parse.urlparse(url)
        dbname = parsed.path[1:]  # Remove leading slash
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        
        # Build connection parameters
        conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "connect_timeout": DEFAULT_TIMEOUT,
            "application_name": "SCARE Unified Dashboard - Troubleshooter"
        }
        
        # Check if we need to add SSL parameters for Railway
        railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if railway_domain and host and (
            host.endswith("railway.app") or 
            host.endswith("railway.internal") or
            "railway" in host
        ):
            logger.info("Adding SSL parameters for Railway connection")
            conn_params["sslmode"] = "require"
        
        return conn_params
    except Exception as e:
        logger.error(f"Error parsing database URL: {str(e)}")
        return {}

def test_network_connectivity(host: str, port: int) -> Tuple[bool, str]:
    """Test basic network connectivity to the database host"""
    logger.info(f"Testing network connectivity to {host}:{port}...")
    
    try:
        # Create a socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(DEFAULT_TIMEOUT)
        
        # Try to connect
        start_time = time.time()
        result = sock.connect_ex((host, port))
        elapsed_time = time.time() - start_time
        
        # Close the socket
        sock.close()
        
        if result == 0:
            logger.info(f"Network connection successful (took {elapsed_time:.2f} seconds)")
            return True, f"Connected to {host}:{port} in {elapsed_time:.2f} seconds"
        else:
            error_msg = f"Network connection failed with error code {result}"
            logger.error(error_msg)
            return False, error_msg
    except socket.gaierror:
        error_msg = f"Hostname {host} could not be resolved"
        logger.error(error_msg)
        return False, error_msg
    except socket.timeout:
        error_msg = f"Connection to {host}:{port} timed out after {DEFAULT_TIMEOUT} seconds"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Network connection error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def test_psycopg2_connection(conn_params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Test PostgreSQL connection using psycopg2"""
    logger.info("Testing PostgreSQL connection using psycopg2...")
    
    results = {
        "success": False,
        "elapsed_time": 0,
        "version": None,
        "tables": [],
        "error": None
    }
    
    try:
        # Try to connect
        start_time = time.time()
        conn = psycopg2.connect(**conn_params)
        elapsed_time = time.time() - start_time
        results["elapsed_time"] = elapsed_time
        
        # Test the connection
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if we can execute a simple query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Get database information
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        results["version"] = version
        
        # List tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        results["tables"] = tables
        
        # Check for required tables
        missing_tables = [table for table in REQUIRED_TABLES if table not in tables]
        if missing_tables:
            logger.warning(f"Missing required tables: {missing_tables}")
            results["missing_tables"] = missing_tables
        
        # Close connection
        cursor.close()
        conn.close()
        
        if result and result[0] == 1:
            logger.info(f"psycopg2 connection successful (took {elapsed_time:.2f} seconds)")
            logger.info(f"Database version: {version}")
            logger.info(f"Tables in database: {len(tables)}")
            results["success"] = True
            return True, f"Connection successful in {elapsed_time:.2f} seconds", results
        else:
            logger.error("psycopg2 connection test query failed")
            results["error"] = "Connection test query failed"
            return False, "Connection test query failed", results
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        logger.error(f"psycopg2 connection failed: {error_msg}")
        results["error"] = error_msg
        return False, error_msg, results
    except Exception as e:
        error_msg = str(e)
        logger.error(f"psycopg2 connection error: {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        results["error"] = error_msg
        return False, error_msg, results

def check_table_columns(conn_params: Dict[str, Any]) -> Dict[str, List[str]]:
    """Check columns in required tables"""
    logger.info("Checking table columns...")
    
    table_columns = {}
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check columns for each required table
        for table in REQUIRED_TABLES:
            try:
                cursor.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                """)
                columns = [row[0] for row in cursor.fetchall()]
                table_columns[table] = columns
                logger.info(f"Table {table} has {len(columns)} columns")
            except Exception as e:
                logger.error(f"Error checking columns for table {table}: {str(e)}")
                table_columns[table] = []
        
        # Close connection
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error checking table columns: {str(e)}")
    
    return table_columns

def check_missing_columns(table_columns: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Check for missing columns in tables"""
    logger.info("Checking for missing columns...")
    
    missing_columns = {}
    
    # Define required columns for each table
    required_columns = {
        "sm_fact_bing_ads": ["network"],
        "sm_fact_google_ads": ["network"],
        "sm_fact_facebook_ads": ["network"],
        "sm_fact_linkedin_ads": ["network"],
        "sm_dim_campaign_mapping": ["network", "pretty_network"]
    }
    
    # Check for missing columns
    for table, columns in required_columns.items():
        if table not in table_columns:
            logger.warning(f"Table {table} not found")
            missing_columns[table] = columns
            continue
        
        existing_columns = table_columns[table]
        missing = [col for col in columns if col not in existing_columns]
        
        if missing:
            logger.warning(f"Table {table} is missing columns: {missing}")
            missing_columns[table] = missing
    
    return missing_columns

def fix_missing_columns(conn_params: Dict[str, Any], missing_columns: Dict[str, List[str]]) -> bool:
    """Fix missing columns in tables"""
    logger.info("Attempting to fix missing columns...")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create migrations table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Fix missing columns for each table
        for table, columns in missing_columns.items():
            for column in columns:
                migration_name = f"add_{column}_to_{table}"
                
                # Check if migration was already applied
                cursor.execute("""
                    SELECT COUNT(*) FROM migrations
                    WHERE migration_name = %s
                """, (migration_name,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    logger.info(f"Migration {migration_name} already applied, skipping")
                    continue
                
                # Add the column
                try:
                    logger.info(f"Adding column {column} to table {table}")
                    
                    # Different default values based on column type
                    if column in ["network", "pretty_network"]:
                        cursor.execute(f"""
                            ALTER TABLE {table}
                            ADD COLUMN IF NOT EXISTS {column} VARCHAR(255) DEFAULT 'Search'
                        """)
                    else:
                        cursor.execute(f"""
                            ALTER TABLE {table}
                            ADD COLUMN IF NOT EXISTS {column} VARCHAR(255)
                        """)
                    
                    # Record the migration
                    cursor.execute("""
                        INSERT INTO migrations (migration_name)
                        VALUES (%s)
                    """, (migration_name,))
                    
                    logger.info(f"Successfully added column {column} to table {table}")
                except Exception as e:
                    logger.error(f"Error adding column {column} to table {table}: {str(e)}")
                    return False
        
        # Close connection
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error fixing missing columns: {str(e)}")
        return False

def test_connection_with_retry(conn_params: Dict[str, Any], max_retries: int = DEFAULT_RETRY_COUNT) -> Tuple[bool, str, Dict[str, Any]]:
    """Test database connection with retries"""
    logger.info(f"Testing database connection with {max_retries} retries...")
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"Connection attempt {attempt}/{max_retries}")
        
        success, message, results = test_psycopg2_connection(conn_params)
        
        if success:
            return success, message, results
        
        if attempt < max_retries:
            delay = DEFAULT_RETRY_DELAY * attempt
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    return False, f"Failed after {max_retries} attempts", {"success": False, "error": "Max retries exceeded"}

def generate_report(
    env_status: Dict[str, str],
    network_status: Tuple[bool, str],
    connection_status: Tuple[bool, str, Dict[str, Any]],
    table_columns: Dict[str, List[str]],
    missing_columns: Dict[str, List[str]],
    fix_attempted: bool = False,
    fix_successful: bool = False
) -> Dict[str, Any]:
    """Generate a comprehensive report of the database troubleshooting"""
    logger.info("Generating troubleshooting report...")
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": {
            "variables": env_status,
            "railway_detected": bool(os.environ.get("RAILWAY_PUBLIC_DOMAIN"))
        },
        "network": {
            "success": network_status[0],
            "message": network_status[1]
        },
        "database": {
            "connection": {
                "success": connection_status[0],
                "message": connection_status[1],
                "details": connection_status[2]
            },
            "tables": {
                "columns": table_columns,
                "missing_columns": missing_columns
            }
        },
        "fixes": {
            "attempted": fix_attempted,
            "successful": fix_successful
        },
        "recommendations": []
    }
    
    # Generate recommendations based on findings
    if not report["environment"]["variables"].get("DATABASE_URL"):
        report["recommendations"].append({
            "issue": "Missing DATABASE_URL",
            "solution": "Set the DATABASE_URL environment variable in Railway"
        })
    
    if not report["network"]["success"]:
        report["recommendations"].append({
            "issue": "Network connectivity issue",
            "solution": "Check if the database is running and accessible from the application"
        })
    
    if not report["database"]["connection"]["success"]:
        error = report["database"]["connection"]["details"].get("error", "")
        if "password authentication failed" in error.lower():
            report["recommendations"].append({
                "issue": "Authentication failed",
                "solution": "Check database username and password in DATABASE_URL"
            })
        elif "does not exist" in error.lower() and "database" in error.lower():
            report["recommendations"].append({
                "issue": "Database does not exist",
                "solution": "Create the database or check the database name in DATABASE_URL"
            })
        else:
            report["recommendations"].append({
                "issue": "Database connection failed",
                "solution": "Check the database URL and ensure the database is running"
            })
    
    if report["database"]["tables"]["missing_columns"]:
        report["recommendations"].append({
            "issue": "Missing columns in tables",
            "solution": "Run the troubleshooter with --fix to add missing columns"
        })
    
    return report

def save_report(report: Dict[str, Any], filename: str = "db_troubleshoot_report.json"):
    """Save the troubleshooting report to a file"""
    try:
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {filename}")
    except (PermissionError, IOError):
        logger.warning("Unable to save report to file, displaying on console only")
        print("\nTROUBLESHOOTING REPORT:")
        print(json.dumps(report, indent=2))

def main():
    """Main function"""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger.info("Starting database troubleshooting...")
    
    # Log environment variables
    env_status = log_environment_variables()
    
    # Get database URL
    database_url = get_database_url()
    if not database_url:
        logger.error("No database URL available. Cannot proceed with test.")
        report = generate_report(
            env_status=env_status,
            network_status=(False, "No database URL available"),
            connection_status=(False, "No database URL available", {"error": "No database URL"}),
            table_columns={},
            missing_columns={},
            fix_attempted=False,
            fix_successful=False
        )
        save_report(report)
        return 1
    
    # Parse database URL
    conn_params = parse_database_url(database_url)
    if not conn_params:
        logger.error("Failed to parse database URL. Cannot proceed with test.")
        report = generate_report(
            env_status=env_status,
            network_status=(False, "Failed to parse database URL"),
            connection_status=(False, "Failed to parse database URL", {"error": "Invalid URL format"}),
            table_columns={},
            missing_columns={},
            fix_attempted=False,
            fix_successful=False
        )
        save_report(report)
        return 1
    
    # Test network connectivity
    network_status = test_network_connectivity(conn_params["host"], conn_params["port"])
    
    # Test database connection
    connection_status = test_connection_with_retry(conn_params, args.retry)
    
    # Check table columns if connection was successful
    table_columns = {}
    missing_columns = {}
    fix_attempted = False
    fix_successful = False
    
    if connection_status[0]:
        table_columns = check_table_columns(conn_params)
        missing_columns = check_missing_columns(table_columns)
        
        # Fix missing columns if requested
        if args.fix and missing_columns:
            fix_attempted = True
            fix_successful = fix_missing_columns(conn_params, missing_columns)
            
            if fix_successful:
                logger.info("Successfully fixed missing columns")
                # Re-check table columns after fix
                table_columns = check_table_columns(conn_params)
                missing_columns = check_missing_columns(table_columns)
            else:
                logger.error("Failed to fix missing columns")
    
    # Generate report
    report = generate_report(
        env_status=env_status,
        network_status=network_status,
        connection_status=connection_status,
        table_columns=table_columns,
        missing_columns=missing_columns,
        fix_attempted=fix_attempted,
        fix_successful=fix_successful
    )
    
    # Save report
    save_report(report)
    
    # Return success or failure
    if connection_status[0] and not missing_columns:
        logger.info("Database troubleshooting completed successfully")
        return 0
    else:
        logger.error("Database troubleshooting completed with issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
