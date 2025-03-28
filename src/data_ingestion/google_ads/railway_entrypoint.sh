#!/bin/bash
# This script is intended to be run as /app/railway_entrypoint.sh

# Enable logging to file for debugging cron issues
LOGFILE="/var/log/google_ads/cron.log"
mkdir -p /var/log/google_ads
# Redirect stdout to log file AND original stdout (for Railway logs)
# Redirect stderr to original stderr (for Railway logs)
exec > >(tee -a ${LOGFILE})
exec 2>&1

echo "========== RAILWAY ENTRYPOINT SCRIPT START (/app/railway_entrypoint.sh) =========="
echo "============ $(date) ============"

# Print all environment variables (without the sensitive ones)
env | grep -v PASSWORD | grep -v SECRET | grep -v TOKEN | sort

echo "Started at: $(date)"
echo "Args: $@"
echo "Command: $0"
echo "Running in Railway environment..."
echo "Current directory: $(pwd)" # Should be /app if run directly

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

# Define absolute paths for Python scripts (assuming they are still under /app/src/...)
MAIN_PY="/app/src/data_ingestion/google_ads/main.py"
FETCH_PY="/app/src/data_ingestion/google_ads/fetch_only.py"
IMPORT_PY="/app/src/data_ingestion/google_ads/import_from_json.py"

# Check if python files exist before trying to run them
if [ ! -f "$MAIN_PY" ]; then
   echo "ERROR: Cannot find main python script at $MAIN_PY"
   exit 1
fi
# Add checks for other scripts if they are essential for all modes
# if [ ! -f "$FETCH_PY" ]; then echo "ERROR: Cannot find fetch script at $FETCH_PY"; exit 1; fi
# if [ ! -f "$IMPORT_PY" ]; then echo "ERROR: Cannot find import script at $IMPORT_PY"; exit 1; fi

echo "Using main script: ${MAIN_PY}"

# Create ETL log file
ETL_LOGFILE="/var/log/google_ads/etl_process.log"
touch ${ETL_LOGFILE}
echo "$(date) - Starting ETL process" >> ${ETL_LOGFILE}

# Determine the command to run
echo "========== COMMAND EXECUTION START =========="
set -x # Enable command tracing
case "$1" in
    fetch)
        echo "Running fetch-only mode..." | tee -a ${ETL_LOGFILE}
        if [ ! -f "$FETCH_PY" ]; then echo "ERROR: Fetch script not found at $FETCH_PY"; exit 1; fi
        python ${FETCH_PY} 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    import)
        echo "Running import mode..." | tee -a ${ETL_LOGFILE}
        if [ ! -f "$IMPORT_PY" ]; then echo "ERROR: Import script not found at $IMPORT_PY"; exit 1; fi
        python ${IMPORT_PY} "${2:-google_ads_data.json}" 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    etl)
        echo "Running full ETL process..." | tee -a ${ETL_LOGFILE}
        echo "Command: python ${MAIN_PY} --days ${2:-7}" | tee -a ${ETL_LOGFILE}
        python ${MAIN_PY} --days "${2:-7}" 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    schedule)
        echo "Running scheduled ETL process via cron..." | tee -a ${ETL_LOGFILE}
        echo "Command: python ${MAIN_PY} --schedule" | tee -a ${ETL_LOGFILE}
        python ${MAIN_PY} --schedule 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    *)
        echo "No specific command provided ($1), defaulting to ETL process..." | tee -a ${ETL_LOGFILE}
        echo "Command: python ${MAIN_PY} --days 7" | tee -a ${ETL_LOGFILE}
        echo "============ EXECUTING MAIN.PY ============" | tee -a ${ETL_LOGFILE}
        python ${MAIN_PY} --days 7 2>&1 | tee -a ${ETL_LOGFILE}
        echo "============ MAIN.PY EXECUTION COMPLETE ============" | tee -a ${ETL_LOGFILE}
        ;;
esac
RESULT=$?
set +x # Disable command tracing

if [ $RESULT -ne 0 ]; then
    echo "========== ERROR: Command failed with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
else
    echo "========== Command completed successfully with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
fi

echo "Script completed at: $(date)"
echo "Check log files at: ${LOGFILE} and ${ETL_LOGFILE}"
echo "========== RAILWAY ENTRYPOINT SCRIPT END (/app/railway_entrypoint.sh) =========="
