#!/bin/bash
# This script is intended to be run as /app/bads_entrypoint.sh

# --- Basic Logging Setup ---
# Create log directory if it doesn't exist
mkdir -p /var/log/bing_ads
LOGFILE="/var/log/bing_ads/cron.log"

# Redirect stdout to log file AND original stdout (for Railway logs)
# Redirect stderr to original stderr (for Railway logs)
exec > >(tee -a ${LOGFILE})
exec 2>&1

echo "========== BING ADS ENTRYPOINT SCRIPT START (/app/bads_entrypoint.sh) =========="
echo "============ $(date) ============"

# --- Environment Setup & Checks ---
# Print relevant environment variables (mask sensitive ones)
echo "--- Environment Variables ---"
env | grep -E 'BING_ADS_|PG|DATABASE_URL|RAILWAY_' | grep -v PASSWORD | sort
echo "PGPASSWORD=**** (masked)" # Explicitly show PGPASSWORD is expected but mask it
echo "---------------------------"

echo "Started at: $(date)"
echo "Args: $@"
echo "Command: $0"
echo "Running in Railway environment..."
echo "Current directory: $(pwd)" # Should be /app

# --- Database URL Handling (Copied from Google Ads Entrypoint) ---
echo "Checking for DATABASE_URL environment variable..."
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL is not set. Checking for fallback variables..."
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
MASKED_URL=$(echo "$DATABASE_URL" | sed -E 's/(postgresql:\/\/)[^:]+:([^@]+@)/\1****:\2/' | sed -E 's/:[^:]+@/:****@/')
echo "Using DATABASE_URL: ${MASKED_URL}"

# --- Define Python Script Path ---
# Assuming the python script is also directly under /app based on previous findings
BING_ADS_MAIN_PY="/app/main.py" # Path within src/data_ingestion/bing_ads/

# Check if the python script exists
echo "Checking for Python script at $BING_ADS_MAIN_PY..."
if [ ! -f "$BING_ADS_MAIN_PY" ]; then
   echo "ERROR: Cannot find Bing Ads python script at $BING_ADS_MAIN_PY"
   echo "--- ls -la /app ---"
   ls -la /app
   exit 1
fi
echo "Found Bing Ads Python script."

# --- Execute Python Script ---
echo "========== COMMAND EXECUTION START =========="
set -x # Enable command tracing

# Pass the argument ($1, e.g., 'schedule') to the python script
python ${BING_ADS_MAIN_PY} "$1" # Pass the first argument directly

RESULT=$?
set +x # Disable command tracing

if [ $RESULT -ne 0 ]; then
    echo "========== ERROR: Bing Ads Python script failed with exit code $RESULT =========="
else
    echo "========== Bing Ads Python script completed successfully with exit code $RESULT =========="
fi

echo "Script completed at: $(date)"
echo "Check log file at: ${LOGFILE}"
echo "========== BING ADS ENTRYPOINT SCRIPT END (/app/bads_entrypoint.sh) =========="