#!/bin/bash

# SCARE Unified Dashboard - Google Ads ETL Service
# Improved entrypoint script for Railway

# Enable logging to file for debugging
LOGDIR="/var/log/google_ads"
mkdir -p $LOGDIR
LOGFILE="$LOGDIR/etl_$(date +%Y%m%d_%H%M%S).log"

# Redirect stdout and stderr to both terminal and log file
exec > >(tee -a "${LOGFILE}")
exec 2>&1

echo "========== IMPROVED RAILWAY ENTRYPOINT SCRIPT START =========="
echo "============ $(date) ============"

# Explicitly export all Google Ads credentials from environment
# This ensures they're available to all child processes
export GOOGLE_ADS_DEVELOPER_TOKEN="${GOOGLE_ADS_DEVELOPER_TOKEN}"
export GOOGLE_ADS_CLIENT_ID="${GOOGLE_ADS_CLIENT_ID}"
export GOOGLE_ADS_CLIENT_SECRET="${GOOGLE_ADS_CLIENT_SECRET}"
export GOOGLE_ADS_REFRESH_TOKEN="${GOOGLE_ADS_REFRESH_TOKEN}"
export GOOGLE_ADS_CUSTOMER_ID="${GOOGLE_ADS_CUSTOMER_ID}"

# Log a masked version of the credentials (for debugging)
echo "Google Ads credentials:"
echo "GOOGLE_ADS_DEVELOPER_TOKEN=${GOOGLE_ADS_DEVELOPER_TOKEN:0:4}****${GOOGLE_ADS_DEVELOPER_TOKEN: -4}"
echo "GOOGLE_ADS_CLIENT_ID=${GOOGLE_ADS_CLIENT_ID}"
echo "GOOGLE_ADS_CLIENT_SECRET=${GOOGLE_ADS_CLIENT_SECRET:0:4}****${GOOGLE_ADS_CLIENT_SECRET: -4}"
echo "GOOGLE_ADS_REFRESH_TOKEN=${GOOGLE_ADS_REFRESH_TOKEN:0:4}****${GOOGLE_ADS_REFRESH_TOKEN: -4}"
echo "GOOGLE_ADS_CUSTOMER_ID=${GOOGLE_ADS_CUSTOMER_ID}"

# Generate a google-ads.yaml file from environment variables
# This is a fallback in case environment variables aren't working directly
cat > google-ads.yaml << EOF
developer_token: ${GOOGLE_ADS_DEVELOPER_TOKEN}
client_id: ${GOOGLE_ADS_CLIENT_ID}
client_secret: ${GOOGLE_ADS_CLIENT_SECRET}
refresh_token: ${GOOGLE_ADS_REFRESH_TOKEN}
login_customer_id: ${GOOGLE_ADS_CUSTOMER_ID}
use_proto_plus: True
EOF

echo "Created google-ads.yaml file from environment variables"

# Log environment info
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Contents of current directory:"
ls -la

# Run the diagnostic script first to check credentials
echo "Running credential diagnostics..."
python src/data_ingestion/google_ads/debug_credentials.py

# Wait for database to be ready
echo "Waiting for database to be ready..."
python -c "
import time
import os
import sys
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

retries = 0
max_retries = 30
db_url = os.environ.get('DATABASE_URL')

if not db_url:
    print('DATABASE_URL environment variable not set')
    sys.exit(1)

print(f'Connecting to database: {db_url.split('@')[1]}')  # Only show the non-credential part

while retries < max_retries:
    try:
        engine = sa.create_engine(db_url)
        conn = engine.connect()
        conn.close()
        print('Successfully connected to the database')
        sys.exit(0)
    except OperationalError as e:
        retries += 1
        print(f'Cannot connect to database, retry {retries}/{max_retries}: {str(e)}')
        time.sleep(2)
    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        sys.exit(1)

print('Failed to connect to database after multiple retries')
sys.exit(1)
"

# Check if this is a cron run or startup run
if [ "$1" == "fetch" ]; then
    # Just fetch data from Google Ads API and save to JSON
    echo "Running Google Ads data fetch..."
    # Run the fetch script with extensive logging
    python src/data_ingestion/google_ads/fetch_to_json.py
    FETCH_RESULT=$?
    
    if [ $FETCH_RESULT -eq 0 ]; then
        echo "Fetch completed successfully"
    else
        echo "Fetch failed with exit code $FETCH_RESULT"
    fi
    
elif [ "$1" == "import" ]; then
    # Import previously fetched data to the database
    echo "Running Google Ads data import..."
    python src/data_ingestion/google_ads/import_from_json.py
    IMPORT_RESULT=$?
    
    if [ $IMPORT_RESULT -eq 0 ]; then
        echo "Import completed successfully"
    else
        echo "Import failed with exit code $IMPORT_RESULT"
    fi
    
else
    # Run the full ETL process
    echo "Running complete Google Ads ETL process..."
    python src/data_ingestion/google_ads/main.py
    ETL_RESULT=$?
    
    if [ $ETL_RESULT -eq 0 ]; then
        echo "ETL process completed successfully"
    else
        echo "ETL process failed with exit code $ETL_RESULT"
    fi
fi

echo "========== ENTRYPOINT SCRIPT FINISHED =========="
echo "See detailed logs in $LOGFILE"
