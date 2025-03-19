#!/bin/bash

set -e

echo "Running in Railway environment..."
echo "Current directory: $(pwd)"
echo "Listing files in app directory:"
ls -la /app
echo "Checking for main.py in multiple locations:"
[ -f /app/main.py ] && echo "Found /app/main.py" || echo "Not found: /app/main.py"
[ -f main.py ] && echo "Found main.py in current directory" || echo "Not found: main.py in current directory"

# Wait for database to be ready (for Docker/Railway deployment)
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

print(f'Connecting to database: {db_url}')

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

# Determine if we're in the right directory
if [ -f main.py ]; then
    SCRIPT_DIR="."
elif [ -f /app/main.py ]; then
    SCRIPT_DIR="/app"
else
    echo "Error: Cannot find main.py in any expected location"
    echo "Current directory: $(pwd)"
    echo "Listing files in current directory:"
    ls -la
    echo "Listing files in /app directory:"
    ls -la /app || echo "Cannot access /app directory"
    exit 1
fi

# Determine the command to run
case "$1" in
    fetch)
        echo "Running fetch-only mode..."
        python ${SCRIPT_DIR}/fetch_only.py
        ;;
    import)
        echo "Running import mode..."
        python ${SCRIPT_DIR}/import_from_json.py "${2:-google_ads_data.json}"
        ;;
    etl)
        echo "Running full ETL process..."
        python ${SCRIPT_DIR}/main.py --days-back "${2:-7}"
        ;;
    schedule)
        echo "Running scheduled ETL process..."
        python ${SCRIPT_DIR}/main.py --schedule
        ;;
    shell)
        echo "Starting interactive shell..."
        /bin/bash
        ;;
    *)
        echo "Usage: $0 {fetch|import|etl|schedule|shell}"
        exit 1
        ;;
esac
