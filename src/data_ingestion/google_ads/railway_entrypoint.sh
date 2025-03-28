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
echo "Current directory: $(pwd)" # Should be /app

# Check if DATABASE_URL is provided by Railway, with fallback
echo "Checking for DATABASE_URL environment variable..."
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL is not set. Checking for RAILS_SERVICE_POSTGRES_URL..."
    if [ -n "$RAILWAY_SERVICE_POSTGRES_URL" ]; then
        echo "Found RAILS_SERVICE_POSTGRES_URL. Using it as DATABASE_URL."
        # Export the URL provided by Railway. Assumes it's the full connection string or Python handles PG vars.
        export DATABASE_URL="${RAILWAY_SERVICE_POSTGRES_URL}"
        echo "Exported DATABASE_URL from RAILS_SERVICE_POSTGRES_URL."
    else
        echo "ERROR: Neither DATABASE_URL nor RAILS_SERVICE_POSTGRES_URL is set."
        echo "Please ensure Railway is injecting database connection variables."
        exit 1
    fi
fi

# Mask the password part for logging (now applied even if fallback was used)
MASKED_URL=$(echo "$DATABASE_URL" | sed -E 's/(postgresql:\/\/)[^:]+:([^@]+@)/\1****:\2/' | sed -E 's/:[^:]+@/:****@/') # Improved masking
echo "Using DATABASE_URL: ${MASKED_URL}"


# Define absolute paths for Python scripts (Updated based on previous errors)
# Assuming scripts are directly under /app now
MAIN_PY="/app/main.py"
FETCH_PY="/app/fetch_only.py"
IMPORT_PY="/app/import_from_json.py"

# Check if python files exist before trying to run them
echo "Checking for Python script at $MAIN_PY..."
if [ ! -f "$MAIN_PY" ]; then
   echo "ERROR: Cannot find main python script at $MAIN_PY"
   # Let's list /app contents for debugging if main.py is missing
   echo "--- ls -la /app ---"
   ls -la /app
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
