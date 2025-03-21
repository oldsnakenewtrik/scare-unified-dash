"""
Database diagnostics script for SCARE Unified Dashboard.
This script tests the database connection and provides detailed information about the status.
"""
import os
import sys
import time
import json
import traceback
import datetime
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_diagnostics")

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test the database connection and provide diagnostic information"""
    try:
        # Get database URL from environment - add more fallbacks
        database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL") or "postgresql://scare_user:scare_password@postgres:5432/scare_metrics"
        
        # Print database URL for debugging (masking password)
        debug_url = database_url
        if "://" in debug_url:
            parts = debug_url.split("://")
            if "@" in parts[1]:
                userpass, hostdb = parts[1].split("@", 1)
                if ":" in userpass:
                    user, password = userpass.split(":", 1)
                    debug_url = f"{parts[0]}://{user}:****@{hostdb}"
        
        logger.info(f"Testing connection to database: {debug_url}")
        
        # Try to create an engine and connect
        start_time = time.time()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            connection_time = time.time() - start_time
            logger.info(f"Connection established in {connection_time:.2f} seconds")
            
            # Test basic query
            query_start = time.time()
            result = conn.execute(text("SELECT 1 as test"))
            query_time = time.time() - query_start
            basic_query_result = result.fetchone()[0]
            logger.info(f"Basic query executed in {query_time:.2f} seconds with result: {basic_query_result}")
            
            # Get database info
            logger.info("Getting database information...")
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
            
            # Check for specific tables
            required_tables = [
                "sm_campaign_name_mapping", 
                "sm_fact_google_ads", 
                "sm_fact_bing_ads", 
                "sm_fact_redtrack", 
                "sm_fact_matomo"
            ]
            
            missing_tables = [table for table in required_tables if table not in tables]
            if missing_tables:
                logger.warning(f"Missing required tables: {', '.join(missing_tables)}")
            else:
                logger.info("All required tables exist")
            
            # Check table data
            table_data = {}
            for table in required_tables:
                if table in tables:
                    try:
                        count_query = f"SELECT COUNT(*) FROM public.{table}"
                        count = conn.execute(text(count_query)).scalar() or 0
                        table_data[table] = count
                        logger.info(f"Table {table} has {count} rows")
                    except Exception as e:
                        logger.error(f"Error checking data in {table}: {str(e)}")
                        table_data[table] = f"ERROR: {str(e)}"
            
            # Check views
            required_views = ["sm_unified_ads_metrics", "sm_campaign_performance"]
            view_data = {}
            for view in required_views:
                if view in tables:
                    try:
                        count_query = f"SELECT COUNT(*) FROM public.{view}"
                        count = conn.execute(text(count_query)).scalar() or 0
                        view_data[view] = count
                        logger.info(f"View {view} has {count} rows")
                    except Exception as e:
                        logger.error(f"Error checking data in view {view}: {str(e)}")
                        view_data[view] = f"ERROR: {str(e)}"
                else:
                    logger.warning(f"Required view does not exist: {view}")
            
            # Check recent data
            recent_data = {}
            if "sm_fact_google_ads" in tables:
                try:
                    recent_query = """
                    SELECT date, COUNT(*) 
                    FROM public.sm_fact_google_ads 
                    GROUP BY date 
                    ORDER BY date DESC 
                    LIMIT 5
                    """
                    recent_results = conn.execute(text(recent_query)).fetchall()
                    recent_data["recent_google_ads"] = [
                        {"date": row[0].isoformat(), "count": row[1]} 
                        for row in recent_results
                    ]
                    logger.info(f"Recent Google Ads data: {recent_data['recent_google_ads']}")
                except Exception as e:
                    logger.error(f"Error checking recent Google Ads data: {str(e)}")
                    recent_data["recent_google_ads"] = f"ERROR: {str(e)}"
            
            # Summarize results
            diagnostics = {
                "status": "success",
                "timestamp": datetime.datetime.now().isoformat(),
                "connection": {
                    "success": True,
                    "time_ms": round(connection_time * 1000, 2),
                    "database_host": database_url.split("@")[1].split("/")[0] if "@" in database_url else "unknown",
                    "railway_internal": "railway.internal" in database_url
                },
                "basic_query": {
                    "success": True,
                    "time_ms": round(query_time * 1000, 2),
                    "result": basic_query_result
                },
                "tables": {
                    "found": len(tables),
                    "names": tables,
                    "missing_required": missing_tables
                },
                "table_data": table_data,
                "views": view_data,
                "recent_data": recent_data
            }
            
            logger.info("Database diagnostics completed successfully")
            return diagnostics
        
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"Database connection test failed: {error_msg}")
        logger.error(traceback_str)
        
        is_network_error = "Network is unreachable" in error_msg or "Could not connect to server" in error_msg
        railway_internal = "railway.internal" in os.getenv("DATABASE_URL", "") if os.getenv("DATABASE_URL") else False
        
        return {
            "status": "error",
            "timestamp": datetime.datetime.now().isoformat(),
            "error": {
                "message": error_msg,
                "traceback": traceback_str,
                "is_network_error": is_network_error,
                "railway_internal": railway_internal
            },
            "recommendations": get_recommendations(error_msg, railway_internal)
        }

def get_recommendations(error_msg, railway_internal):
    """Generate recommendations based on the error message"""
    recommendations = []
    
    if "Network is unreachable" in error_msg:
        if railway_internal:
            recommendations.append("Ensure Private Networking is enabled for this service in Railway")
            recommendations.append("Check that both database and app services are in the same project and environment")
            recommendations.append("Verify the database service is running and healthy in Railway")
        else:
            recommendations.append("Check if the database host is accessible from your network")
            recommendations.append("Verify firewall settings allow connections to the database port")
    
    elif "connection refused" in error_msg.lower():
        recommendations.append("Verify that the database server is running")
        recommendations.append("Check if the database port is correct and open")
    
    elif "password authentication failed" in error_msg.lower():
        recommendations.append("Verify your database username and password")
        recommendations.append("Check if the DATABASE_URL environment variable is correctly set")
    
    elif "does not exist" in error_msg and "database" in error_msg.lower():
        recommendations.append("Create the specified database")
        recommendations.append("Check if the database name in the connection string is correct")
    
    elif "no pg_hba.conf entry" in error_msg.lower():
        recommendations.append("Update the PostgreSQL authentication configuration to allow your connection")
        recommendations.append("Check if the database is configured to allow connections from your IP")
    
    else:
        recommendations.append("Check that the DATABASE_URL environment variable is correctly set")
        recommendations.append("Verify the database server is running and accessible")
        recommendations.append("Check PostgreSQL logs for more detailed error information")
    
    if railway_internal:
        recommendations.append("Contact Railway support if you continue to have issues with private networking")
    
    return recommendations

if __name__ == "__main__":
    """Run the database diagnostics script"""
    results = test_database_connection()
    
    # Print results in a readable format
    if results["status"] == "success":
        print("\n=== DATABASE DIAGNOSTICS RESULTS ===")
        print(json.dumps(results, indent=4))
    else:
        print("\n=== DATABASE DIAGNOSTICS RESULTS ===")
        print(json.dumps(results, indent=4))
    
    print("\n=== END OF DIAGNOSTICS ===")
