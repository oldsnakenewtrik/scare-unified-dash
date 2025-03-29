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
echo "Args: $@" # Check if 'schedule' appears here
echo "Command: $0"
echo "Running in Railway environment..."
echo "Current directory: $(pwd)" # Should be /app

# Check if DATABASE_URL is provided by Railway, with fallback
echo "Checking for DATABASE_URL environment variable..."
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL is not set. Checking for fallback variables..."
    # Prioritize RAILS_SERVICE_POSTGRES_URL for hostname, then PGHOST
    DB_HOST_FROM_RAILWAY="${RAILWAY_SERVICE_POSTGRES_URL}" # This seems to be just the host
    DB_HOST="${DB_HOST_FROM_RAILWAY:-$PGHOST}" # Use Railway-provided host first

    DB_PORT="${PGPORT:-5432}"
    DB_NAME="${PGDATABASE:-railway}" # Default Railway DB name
    DB_USER="${PGUSER:-postgres}" # Default Railway user

    if [ -z "$DB_HOST" ]; then
         echo "ERROR: Cannot determine DB host (checked RAILS_SERVICE_POSTGRES_URL and PGHOST)."
         exit 1
    fi
    if [ -z "$PGPASSWORD" ]; then
         # Re-check if PGPASSWORD was explicitly set in Railway Variables for this service
         echo "ERROR: PGPASSWORD is not set. Cannot construct fallback DATABASE_URL."
         echo "Ensure PGPASSWORD is set in the Railway service variables."
         exit 1
    fi

    echo "Constructing DATABASE_URL from fallback variables (Host: $DB_HOST)..."
    export DATABASE_URL="postgresql://${DB_USER}:${PGPASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    echo "Exported fallback DATABASE_URL."

else
    echo "DATABASE_URL was already set."
    # Ensure it starts with postgresql:// for SQLAlchemy
    if [[ "$DATABASE_URL" != postgresql://* ]]; then
        echo "Warning: DATABASE_URL does not start with postgresql://. Attempting to fix..."
        FIXED_URL=$(echo "$DATABASE_URL" | sed 's/^postgres:\/\//postgresql:\/\//')
        if [[ "$FIXED_URL" == postgresql://* ]]; then
            export DATABASE_URL="$FIXED_URL"
            echo "Fixed DATABASE_URL prefix."
        else
            echo "ERROR: Could not fix DATABASE_URL prefix. Original value: $DATABASE_URL"
            exit 1
        fi
    fi
fi

# Mask the password part for logging
MASKED_URL=$(echo "$DATABASE_URL" | sed -E 's/(postgresql:\/\/)[^:]+:([^@]+@)/\1****:\2/' | sed -E 's/:[^:]+@/:****@/') # Improved masking
echo "Using DATABASE_URL: ${MASKED_URL}"


# Define absolute paths for Python scripts
MAIN_PY="/app/main.py"
FETCH_PY="/app/fetch_only.py"
IMPORT_PY="/app/import_from_json.py"

# Check if python files exist before trying to run them
echo "Checking for Python script at $MAIN_PY..."
if [ ! -f "$MAIN_PY" ]; then
   echo "ERROR: Cannot find main python script at $MAIN_PY"
   echo "--- ls -la /app ---"
   ls -la /app
   exit 1
fi

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
        # Corrected command: Use --run-once instead of --schedule
        # Assuming a 7-day lookback for scheduled runs, adjust --days if needed
        echo "Command: python ${MAIN_PY} --run-once --days 7" | tee -a ${ETL_LOGFILE}
        python ${MAIN_PY} --run-once --days 7 2>&1 | tee -a ${ETL_LOGFILE}
        ;;
    *)
        # Check if an argument was passed - if so, it's an unknown command
        if [ -n "$1" ]; then
             echo "ERROR: Unknown command provided: '$1'" | tee -a ${ETL_LOGFILE}
             echo "Expected 'fetch', 'import', 'etl', or 'schedule'." | tee -a ${ETL_LOGFILE}
             exit 1 # Exit with error for unknown command
        fi
        # If no argument was passed, default to ETL (as before)
        echo "No specific command provided, defaulting to ETL process..." | tee -a ${ETL_LOGFILE}
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
