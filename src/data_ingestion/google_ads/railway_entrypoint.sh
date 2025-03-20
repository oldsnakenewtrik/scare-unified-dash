#!/bin/bash

# Enable logging to file for debugging cron issues
LOGFILE="/var/log/google_ads/cron.log"
mkdir -p /var/log/google_ads
exec > >(tee -a ${LOGFILE})
exec 2>&1

echo "========== RAILWAY ENTRYPOINT SCRIPT START =========="
echo "============ $(date) ============"

# Print all environment variables (without the sensitive ones)
env | grep -v PASSWORD | grep -v SECRET | grep -v TOKEN | sort

echo "Started at: $(date)"
echo "Args: $@"
echo "Command: $0"
echo "Running in Railway environment..."
echo "Current directory: $(pwd)"
echo "Listing files in current directory:"
ls -la
echo "Listing files in app directory:"
ls -la /app || echo "Cannot access /app directory"

# Check Python installation and packages
echo "Python version:"
python --version
echo "Pip version:"
pip --version
echo "Installed packages:"
pip list

# Create a fallback directory where we'll copy everything
mkdir -p /tmp/google_ads_scripts
echo "Created fallback directory at /tmp/google_ads_scripts"

# Copy all Python files to the fallback directory
echo "Copying Python files to fallback directory..."
find /app -name "*.py" -exec cp {} /tmp/google_ads_scripts/ \; || echo "Failed to copy files from /app"
find . -name "*.py" -exec cp {} /tmp/google_ads_scripts/ \; || echo "Failed to copy files from current directory"

echo "Contents of fallback directory:"
ls -la /tmp/google_ads_scripts

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
    echo "Found main.py in current directory"
    SCRIPT_DIR="."
elif [ -f /app/main.py ]; then
    echo "Found main.py in /app directory"
    SCRIPT_DIR="/app"
elif [ -f /tmp/google_ads_scripts/main.py ]; then
    echo "Found main.py in fallback directory"
    SCRIPT_DIR="/tmp/google_ads_scripts"
else
    echo "ERROR: Cannot find main.py in any expected location"
    echo "Checking PATH environment:"
    echo $PATH
    echo "Trying to execute Python directly:"
    python --version
    # List all python files anywhere in the system
    echo "Searching for main.py in entire filesystem:"
    find / -name "main.py" 2>/dev/null
    exit 1
fi

echo "Using scripts from: ${SCRIPT_DIR}"

# Create a secondary log file specifically for the ETL process
ETL_LOGFILE="/var/log/google_ads/etl_process.log"
touch ${ETL_LOGFILE}
echo "$(date) - Starting ETL process" >> ${ETL_LOGFILE}

# Determine the command to run
echo "========== COMMAND EXECUTION START =========="
set -x  # Enable debugging
case "$1" in
    fetch)
        echo "Running fetch-only mode..." | tee -a ${ETL_LOGFILE}
        python ${SCRIPT_DIR}/fetch_only.py 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    import)
        echo "Running import mode..." | tee -a ${ETL_LOGFILE}
        python ${SCRIPT_DIR}/import_from_json.py "${2:-google_ads_data.json}" 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    etl)
        echo "Running full ETL process..." | tee -a ${ETL_LOGFILE}
        echo "Command: python ${SCRIPT_DIR}/main.py --days ${2:-7}" | tee -a ${ETL_LOGFILE}
        python ${SCRIPT_DIR}/main.py --days "${2:-7}" 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    schedule)
        echo "Running scheduled ETL process via cron..." | tee -a ${ETL_LOGFILE}
        echo "Command: python ${SCRIPT_DIR}/main.py --schedule" | tee -a ${ETL_LOGFILE}
        python ${SCRIPT_DIR}/main.py --schedule 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    *)
        echo "No specific command provided, defaulting to ETL process..." | tee -a ${ETL_LOGFILE}
        echo "Command: python ${SCRIPT_DIR}/main.py --days 7" | tee -a ${ETL_LOGFILE}
        echo "============ EXECUTING MAIN.PY ============" | tee -a ${ETL_LOGFILE}
        python ${SCRIPT_DIR}/main.py --days 7 2>&1 | tee -a ${ETL_LOGFILE}
        echo "============ MAIN.PY EXECUTION COMPLETE ============" | tee -a ${ETL_LOGFILE}
        ;;
esac
RESULT=$?
set +x  # Disable debugging

if [ $RESULT -ne 0 ]; then
    echo "========== ERROR: Command failed with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
    echo "Python path:" | tee -a ${ETL_LOGFILE}
    python -c "import sys; print(sys.path)" | tee -a ${ETL_LOGFILE}
    echo "Trying to import pandas directly:" | tee -a ${ETL_LOGFILE}
    python -c "import pandas; print(f'Pandas version: {pandas.__version__}')" | tee -a ${ETL_LOGFILE} || echo "Failed to import pandas" | tee -a ${ETL_LOGFILE}
    echo "Trying to import other libraries:" | tee -a ${ETL_LOGFILE}
    python -c "import sqlalchemy; print(f'SQLAlchemy version: {sqlalchemy.__version__}')" | tee -a ${ETL_LOGFILE} || echo "Failed to import sqlalchemy" | tee -a ${ETL_LOGFILE}
    python -c "import google; print(f'Google version: {google.__version__}')" | tee -a ${ETL_LOGFILE} || echo "Failed to import google" | tee -a ${ETL_LOGFILE}
else
    echo "========== Command completed successfully with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
fi

# Make a copy of the ETL log to a persistent location
echo "ETL Log contents:"
cat ${ETL_LOGFILE}

echo "Script completed at: $(date)"
echo "Check log files at: ${LOGFILE} and ${ETL_LOGFILE}"
echo "========== RAILWAY ENTRYPOINT SCRIPT END =========="
