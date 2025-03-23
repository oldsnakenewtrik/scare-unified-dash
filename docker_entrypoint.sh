#!/bin/bash
set -e

# Print environment info (for debugging)
echo "Starting SCARE Unified Dashboard..."
echo "Python path: $PYTHONPATH"
echo "Working directory: $(pwd)"

# Added detailed port debugging
echo "============== PORT DEBUGGING =============="
echo "RAILWAY_PORT: ${RAILWAY_PORT:-not set}"
echo "PORT: ${PORT:-not set}"
echo "DEFAULT PORT: 5432"
echo "ACTUAL PORT USED: ${PORT:-5432}"
echo "============================================"

# Create data directory if it doesn't exist
mkdir -p ./data

# Run port debug script
echo "Running port debug script..."
python ./src/api/port_debug.py

# Check PostgreSQL connection using the DATABASE_URL environment variable directly
echo "Checking database connection..."
if python -c "
import os
import sys
print('Python version:', sys.version)
print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'Not set').replace('postgres://', 'postgresql://'))
print('PGHOST:', os.environ.get('PGHOST', 'Not set'))
print('PGUSER:', os.environ.get('PGUSER', 'Not set'))
print('PGDATABASE:', os.environ.get('PGDATABASE', 'Not set'))
print('PGPORT:', os.environ.get('PGPORT', 'Not set'))
"; then
    echo "Database environment variables printed successfully"
else
    echo "Warning: Could not print database environment variables"
fi

# Set default port if not provided - use 5432 which is the port Railway expects
export PORT="${PORT:-5432}"
echo "Using PORT: $PORT"

# Enhanced port debugging before server starts
echo "============== FINAL PORT CHECK =============="
echo "FINAL PORT TO BE USED BY UVICORN: $PORT"
echo "=============================================="

# Start the API server with WebSocket support
echo "Starting web server with CORS and WebSocket support..."
echo "Using PORT: $PORT"
exec python -m uvicorn src.api.main:app --host 0.0.0.0 --port $PORT --log-level debug
