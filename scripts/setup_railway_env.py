"""
Script to help set up the correct environment variables for local development
This script will fetch the public database URL from Railway and create a .env.local file
"""
import os
import sys
import logging
import subprocess
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("setup_railway_env")

def get_railway_variables():
    """Get all Railway variables using the Railway CLI"""
    try:
        # Run railway variables command to get all variables
        logger.info("Running 'railway variables' to get database information...")
        result = subprocess.run(
            ["railway", "variables"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        variables = {}
        for line in result.stdout.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                variables[key.strip()] = value.strip()
        
        return variables
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Railway CLI: {e}")
        logger.error(f"Output: {e.output}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

def create_env_file(variables):
    """Create a .env.local file with the necessary variables"""
    if not variables:
        logger.error("No variables to write to .env.local")
        return False
    
    # Create the .env.local file
    env_file = Path(".env.local")
    
    # Check if file exists
    if env_file.exists():
        logger.warning(f"{env_file} already exists. Creating backup...")
        backup_file = Path(f".env.local.bak")
        env_file.rename(backup_file)
        logger.info(f"Backup created at {backup_file}")
    
    # Write variables to file
    with open(env_file, "w") as f:
        # First, write the DATABASE_URL if available
        if "DATABASE_URL" in variables:
            f.write(f"DATABASE_URL={variables['DATABASE_URL']}\n")
        
        # Then, write the DATABASE_PUBLIC_URL if available
        if "DATABASE_PUBLIC_URL" in variables:
            f.write(f"DATABASE_PUBLIC_URL={variables['DATABASE_PUBLIC_URL']}\n")
        
        # Write individual PostgreSQL variables
        for var in ["PGHOST", "PGUSER", "PGPASSWORD", "PGDATABASE", "PGPORT"]:
            if var in variables:
                f.write(f"{var}={variables[var]}\n")
        
        # Write any other variables
        for key, value in variables.items():
            if key not in ["DATABASE_URL", "DATABASE_PUBLIC_URL", "PGHOST", "PGUSER", "PGPASSWORD", "PGDATABASE", "PGPORT"]:
                f.write(f"{key}={value}\n")
    
    logger.info(f"Created {env_file} with Railway variables")
    return True

def main():
    """Main function"""
    logger.info("Setting up local environment for Railway development...")
    
    # Get Railway variables
    variables = get_railway_variables()
    if not variables:
        logger.error("Failed to get Railway variables")
        return False
    
    # Create .env.local file
    success = create_env_file(variables)
    if not success:
        logger.error("Failed to create .env.local file")
        return False
    
    logger.info("Local environment setup complete!")
    logger.info("You can now run your application locally with:")
    logger.info("python -m src.api.main")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("Failed to set up local environment")
        sys.exit(1)
    sys.exit(0)
