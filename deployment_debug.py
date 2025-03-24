#!/usr/bin/env python
"""
Deployment Debugging Helper for SCARE Unified Dashboard

This script verifies current deployment environment and configuration to help
troubleshoot 404 errors and deployment issues.

Run this on Railway with:
railway run python deployment_debug.py
"""

import os
import sys
import json
import logging
import subprocess
import platform
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_git_info():
    """Get Git branch and commit information"""
    try:
        # Get current branch
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            universal_newlines=True
        ).strip()
        
        # Get current commit
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            universal_newlines=True
        ).strip()
        
        # Get commit message
        message = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"], 
            universal_newlines=True
        ).strip()
        
        return {
            "branch": branch,
            "commit": commit,
            "message": message
        }
    except Exception as e:
        logger.error(f"Failed to get Git info: {str(e)}")
        return {
            "branch": "unknown",
            "commit": "unknown",
            "message": "Error fetching Git info"
        }

def get_environment_info():
    """Get environment information"""
    env_vars = {
        # Railway variables
        "RAILWAY_ENVIRONMENT": os.environ.get("RAILWAY_ENVIRONMENT", "Not set"),
        "RAILWAY_SERVICE_NAME": os.environ.get("RAILWAY_SERVICE_NAME", "Not set"),
        
        # Database variables (masked for security)
        "DATABASE_URL": "***masked***" if os.environ.get("DATABASE_URL") else "Not set",
        "PGHOST": os.environ.get("PGHOST", "Not set"),
        "PGDATABASE": os.environ.get("PGDATABASE", "Not set"),
        "PGUSER": "***masked***" if os.environ.get("PGUSER") else "Not set",
        
        # Port
        "PORT": os.environ.get("PORT", "Not set"),
        
        # Python environment
        "PYTHONPATH": os.environ.get("PYTHONPATH", "Not set"),
    }
    
    return {
        "environment_variables": env_vars,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "timestamp": datetime.now().isoformat()
    }

def check_file_exists(path):
    """Check if a file exists"""
    return os.path.exists(path)

def check_api_routes():
    """Check if API route files exist in expected locations"""
    api_files = {
        "main.py": check_file_exists("src/api/main.py"),
        "db_config.py": check_file_exists("src/api/db_config.py"),
        "db_init.py": check_file_exists("src/api/db_init.py"),
        "websocket.py": check_file_exists("src/api/websocket.py")
    }
    
    # Check for route declarations within main.py (simplified check)
    routes_check = {}
    try:
        if api_files["main.py"]:
            with open("src/api/main.py", "r") as f:
                content = f.read()
                routes_check = {
                    "campaigns-hierarchical": "@app.get(\"/api/campaigns-hierarchical\"" in content,
                    "campaigns-performance": "@app.get(\"/api/campaigns-performance\"" in content,
                    "campaign-metrics": "@app.get(\"/api/campaign-metrics\"" in content,
                    "campaign-mappings": "@app.get(\"/api/campaign-mappings\"" in content
                }
    except Exception as e:
        logger.error(f"Error checking routes in main.py: {str(e)}")
        routes_check = {"error": str(e)}
    
    return {
        "api_files": api_files,
        "route_declarations": routes_check
    }

def main():
    """Main function to run all checks"""
    results = {
        "git_info": get_git_info(),
        "environment": get_environment_info(),
        "api_routes": check_api_routes(),
        "working_directory": os.getcwd()
    }
    
    # Print results in a readable format
    logger.info("=== SCARE Unified Dashboard Deployment Debug ===")
    logger.info(f"Timestamp: {results['environment']['timestamp']}")
    logger.info(f"Working Directory: {results['working_directory']}")
    logger.info("\n=== Git Information ===")
    logger.info(f"Branch: {results['git_info']['branch']}")
    logger.info(f"Commit: {results['git_info']['commit']}")
    logger.info(f"Commit Message: {results['git_info']['message']}")
    
    logger.info("\n=== Environment Variables ===")
    for key, value in results['environment']['environment_variables'].items():
        logger.info(f"{key}: {value}")
    
    logger.info(f"\nPython Version: {results['environment']['python_version']}")
    logger.info(f"Platform: {results['environment']['platform']}")
    
    logger.info("\n=== API Files Check ===")
    for file, exists in results['api_routes']['api_files'].items():
        logger.info(f"{file}: {'Found' if exists else 'MISSING'}")
    
    logger.info("\n=== API Routes Check ===")
    for route, exists in results['api_routes']['route_declarations'].items():
        logger.info(f"/api/{route}: {'Declared' if exists else 'NOT FOUND'}")
    
    logger.info("\n=== Summary ===")
    issues = []
    
    # Check for potential issues
    if results['git_info']['branch'] != "feature/campaign-name-mapping":
        issues.append("⚠️ Not deploying from feature/campaign-name-mapping branch")
    
    if not all(results['api_routes']['api_files'].values()):
        issues.append("⚠️ Some API files are missing")
    
    if not all(results['api_routes']['route_declarations'].values()):
        issues.append("⚠️ Some API routes are not declared in main.py")
    
    if not issues:
        logger.info("✅ No obvious deployment issues detected")
    else:
        for issue in issues:
            logger.info(issue)
    
    # Save results to a JSON file for reference
    with open("deployment_debug_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("\nResults saved to deployment_debug_results.json")

if __name__ == "__main__":
    main()
