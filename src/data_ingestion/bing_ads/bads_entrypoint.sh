#!/bin/bash
# Entrypoint script for Bing Ads data ingestion in Railway

# --- Basic Setup ---
LOGFILE="/var/log/bing_ads/cron.log"
mkdir -p /var/log/bing_ads
exec > >(tee -a ${LOGFILE})
exec 2>&1

echo "========== BADS ENTRYPOINT SCRIPT START (/app/bads_entrypoint.sh) =========="
echo "============ $(date) ============"

# Print non-sensitive environment variables
env | grep -v PASSWORD | grep -v SECRET | grep -v TOKEN | sort

echo "Started at: $(date)"
echo "Args: $@"
echo "Command: $0"
echo "Running in Railway environment..."
echo "Current directory: $(pwd)" # Should be /app

# --- Database URL Handling ---
echo "Checking for DATABASE_URL environment variable..."
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL is not set. Checking for fallback variables..."
    DB_HOST_FROM_RAILWAY="${RAILWAY_SERVICE_POSTGRES_URL}"
    DB_HOST="${DB_HOST_FROM_RAILWAY:-$PGHOST}"
    DB_PORT="${PGPORT:-5432}"
    DB_NAME="${PGDATABASE:-railway}"
    DB_USER="${PGUSER:-postgres}"

    if [ -z "$DB_HOST" ]; then
        echo "ERROR: Cannot determine DB host (checked RAILWAY_SERVICE_POSTGRES_URL and PGHOST)." >&2
        exit 1
    fi
    if [ -z "$PGPASSWORD" ]; then
        echo "ERROR: PGPASSWORD is not set. Cannot construct fallback DATABASE_URL." >&2
        echo "Ensure PGPASSWORD is set in the Railway service variables." >&2
        exit 1
    fi
    echo "Constructing DATABASE_URL from fallback variables (Host: $DB_HOST)..."
    export DATABASE_URL="postgresql://${DB_USER}:${PGPASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    echo "Exported fallback DATABASE_URL."
else
    echo "DATABASE_URL was already set."
    if [[ "$DATABASE_URL" != postgresql://* ]]; then
        echo "Warning: DATABASE_URL does not start with postgresql://. Attempting to fix..."
        FIXED_URL=$(echo "$DATABASE_URL" | sed 's/^postgres:\/\//postgresql:\/\//')
        if [[ "$FIXED_URL" == postgresql://* ]]; then
            export DATABASE_URL="$FIXED_URL"
            echo "Fixed DATABASE_URL prefix."
        else
            echo "ERROR: Could not fix DATABASE_URL prefix. Original value: $DATABASE_URL" >&2
            exit 1
        fi
    fi
fi
MASKED_URL=$(echo "$DATABASE_URL" | sed -E 's/(postgresql:\/\/)[^:]+:([^@]+@)/\1****:\2/' | sed -E 's/:[^:]+@/:****@/')
echo "Using DATABASE_URL: ${MASKED_URL}"

# --- Python Script Setup ---
MAIN_PY="/app/main.py"
ETL_LOGFILE="/var/log/bing_ads/etl_process.log"

echo "Checking for Python script at $MAIN_PY..."
if [ ! -f "$MAIN_PY" ]; then
   echo "ERROR: Cannot find main Bing Ads python script at $MAIN_PY" >&2
   echo "--- ls -la /app ---" >&2
   ls -la /app >&2
   exit 1
fi
echo "Found Bing Ads Python script."

touch ${ETL_LOGFILE}
echo "---------------------------" >> ${ETL_LOGFILE}
echo "$(date) - Starting Bing Ads process (Args: $@)" >> ${ETL_LOGFILE}

# --- Command Execution Logic ---
echo "========== COMMAND EXECUTION START =========="
set -x # Enable command tracing

# Default arguments for backfill if not provided
START_DATE_ARG=""
END_DATE_ARG=""

case "$1" in
    schedule)
        echo "Running scheduled fetch mode (--run-once --days 7)..." | tee -a ${ETL_LOGFILE}
        # Execute python script and capture its exit code, not tee's
        python ${MAIN_PY} --run-once --days 7 2>&1 | tee -a ${ETL_LOGFILE}
        RESULT=${PIPESTATUS[0]} # Capture python's exit code from the pipeline
        ;;
    backfill)
        # Extract --start-date and --end-date
        shift # Remove "backfill" argument
        while [[ $# -gt 0 ]]; do
            case $1 in
                --start-date)
                    if [[ -n "$2" ]]; then
                        START_DATE_ARG="$2"
                        shift 2
                    else
                        echo "ERROR: --start-date requires a value." >&2 | tee -a ${ETL_LOGFILE}
                        exit 1
                    fi
                    ;;
                --end-date)
                    if [[ -n "$2" ]]; then
                        END_DATE_ARG="$2"
                        shift 2
                    else
                        echo "ERROR: --end-date requires a value." >&2 | tee -a ${ETL_LOGFILE}
                        exit 1
                    fi
                    ;;
                *)
                    echo "ERROR: Unknown argument for backfill: $1" >&2 | tee -a ${ETL_LOGFILE}
                    exit 1
                    ;;
            esac
        done

        if [ -z "${START_DATE_ARG}" ]; then
             echo "ERROR: --start-date is required for backfill mode." >&2 | tee -a ${ETL_LOGFILE}
             exit 1
        fi

        # Construct command with optional end date
        BACKFILL_CMD="python ${MAIN_PY} --backfill --start-date ${START_DATE_ARG}"
        if [ -n "${END_DATE_ARG}" ]; then
            BACKFILL_CMD="${BACKFILL_CMD} --end-date ${END_DATE_ARG}"
        fi

        echo "Running in backfill mode..." | tee -a ${ETL_LOGFILE}
        echo "Command: ${BACKFILL_CMD}" | tee -a ${ETL_LOGFILE}
        # Execute python script and capture its exit code, not tee's
        eval ${BACKFILL_CMD} 2>&1 | tee -a ${ETL_LOGFILE}
        RESULT=${PIPESTATUS[0]} # Capture python's exit code from the pipeline
        ;;
    *)
        echo "ERROR: Unknown or missing command. Expected 'schedule' or 'backfill'." >&2 | tee -a ${ETL_LOGFILE}
        echo "Provided args: $@" >&2 | tee -a ${ETL_LOGFILE}
        RESULT=1 # Set non-zero result for error
        ;;
esac

set +x # Disable command tracing

# --- Script Completion ---
if [ $RESULT -ne 0 ]; then
    echo "========== ERROR: Bing Ads Python script failed with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
else
    echo "========== Bing Ads Python script completed successfully with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
fi

echo "Script completed at: $(date)"
echo "Check log files at: ${LOGFILE} and ${ETL_LOGFILE}"
echo "========== BADS ENTRYPOINT SCRIPT END (/app/bads_entrypoint.sh) =========="

exit $RESULT # Exit with the Python script's result code