#!/bin/bash
echo "Script started at $(date)" > /tmp/entrypoint_start.log # IMMEDIATE LOG TEST

# Enable logging to file for debugging cron issues
LOGFILE="/var/log/google_ads/cron.log"
mkdir -p /var/log/google_ads || echo "Failed to create log dir" >> /tmp/entrypoint_start.log # Log dir creation attempt
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

# Check if DATABASE_URL is provided by Railway
echo "Checking for DATABASE_URL environment variable..."
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set."
    echo "Please ensure Railway is injecting the DATABASE_URL variable."
    exit 1
else
    # Mask the password part for logging
    MASKED_URL=$(echo "$DATABASE_URL" | sed -E 's/:[^:]+@/:****@/')
    echo "DATABASE_URL is set: ${MASKED_URL}"
fi

# Optional: Add a quick connection test here if needed, but main.py should handle it
# python -c "import os, sqlalchemy; sqlalchemy.create_engine(os.environ['DATABASE_URL']).connect().close(); print('Quick DB connection test successful.')" || exit 1

# Determine script directory (same as before)
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
    exit 1
fi

echo "Using scripts from: ${SCRIPT_DIR}"

# Create ETL log file (same as before)
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
