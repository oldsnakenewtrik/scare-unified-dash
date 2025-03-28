#!/bin/bash
# === IMMEDIATE DIAGNOSTICS ===
# Redirect stderr early to capture potential early errors or trace output
exec 2> /tmp/entrypoint_stderr.log
# Enable command tracing (output goes to stderr, which is now /tmp/entrypoint_stderr.log)
set -x

# Log script start and attempt diagnostics to a separate file
echo "Script started at $(date)" > /tmp/entrypoint_start.log
echo "Attempting diagnostics..." >> /tmp/entrypoint_start.log

# Log current working directory
echo "--- pwd ---" >> /tmp/entrypoint_start.log
pwd >> /tmp/entrypoint_start.log 2>&1

# List directories at various levels to understand the filesystem structure
echo "--- ls -la / ---" >> /tmp/entrypoint_start.log
ls -la / >> /tmp/entrypoint_start.log 2>&1 || echo "Failed to ls /" >> /tmp/entrypoint_start.log

echo "--- ls -la /app ---" >> /tmp/entrypoint_start.log
ls -la /app >> /tmp/entrypoint_start.log 2>&1 || echo "Failed to ls /app" >> /tmp/entrypoint_start.log

echo "--- ls -la /app/src ---" >> /tmp/entrypoint_start.log
ls -la /app/src >> /tmp/entrypoint_start.log 2>&1 || echo "Failed to ls /app/src" >> /tmp/entrypoint_start.log

echo "--- ls -la /app/src/data_ingestion ---" >> /tmp/entrypoint_start.log
ls -la /app/src/data_ingestion >> /tmp/entrypoint_start.log 2>&1 || echo "Failed to ls /app/src/data_ingestion" >> /tmp/entrypoint_start.log

echo "--- ls -la /app/src/data_ingestion/google_ads ---" >> /tmp/entrypoint_start.log
ls -la /app/src/data_ingestion/google_ads >> /tmp/entrypoint_start.log 2>&1 || echo "Failed to ls /app/src/data_ingestion/google_ads" >> /tmp/entrypoint_start.log

echo "Diagnostics finished. Proceeding..." >> /tmp/entrypoint_start.log

# === ORIGINAL SCRIPT START (Modified) ===
# Setup main log file for stdout
LOGFILE="/var/log/google_ads/cron.log"
mkdir -p /var/log/google_ads || echo "Failed to create log dir" >> /tmp/entrypoint_start.log # Log dir creation attempt

# Redirect stdout to main log file (stderr continues to /tmp/entrypoint_stderr.log)
exec 1> >(tee -a ${LOGFILE})

echo "========== RAILWAY ENTRYPOINT SCRIPT START (Main Log) ==========" # This goes to LOGFILE
echo "============ $(date) ============"

# Print all environment variables (without the sensitive ones)
env | grep -v PASSWORD | grep -v SECRET | grep -v TOKEN | sort

echo "Started at: $(date)"
echo "Args: $@"
echo "Command: $0"
echo "Running in Railway environment..."
echo "Current directory: $(pwd)" # Should match pwd logged earlier

# Check if DATABASE_URL is provided by Railway
echo "Checking for DATABASE_URL environment variable..."
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set."
    echo "Please ensure Railway is injecting the DATABASE_URL variable."
    exit 1 # Exit here if no DB URL
else
    # Mask the password part for logging
    MASKED_URL=$(echo "$DATABASE_URL" | sed -E 's/:[^:]+@/:****@/')
    echo "DATABASE_URL is set: ${MASKED_URL}"
fi

# Define absolute paths for Python scripts
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
# set -x was enabled earlier and logs to /tmp/entrypoint_stderr.log
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

if [ $RESULT -ne 0 ]; then
    echo "========== ERROR: Command failed with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
    # Error details should be in /tmp/entrypoint_stderr.log due to set -x and python errors going to stderr
else
    echo "========== Command completed successfully with exit code $RESULT ==========" | tee -a ${ETL_LOGFILE}
fi

# Make a copy of the ETL log to a persistent location if needed
echo "ETL Log contents:"
cat ${ETL_LOGFILE}

echo "Script completed at: $(date)"
echo "Check log files at: ${LOGFILE} and ${ETL_LOGFILE}"
echo "Also check diagnostic logs: /tmp/entrypoint_start.log and /tmp/entrypoint_stderr.log"
echo "========== RAILWAY ENTRYPOINT SCRIPT END (Main Log) =========="

set +x # Disable tracing at the very end
