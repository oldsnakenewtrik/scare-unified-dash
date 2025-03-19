#!/bin/bash
set -e

# Print environment info (for debugging)
echo "Starting SCARE Unified Dashboard..."
echo "Python path: $PYTHONPATH"
echo "Working directory: $(pwd)"

# Create data directory if it doesn't exist
mkdir -p /app/data

# Start Google Ads ETL service in the background
echo "Starting Google Ads ETL service..."
python /app/src/data_ingestion/google_ads/main.py --service &
GOOGLE_ADS_PID=$!

# Wait a moment to ensure the service starts
sleep 2

# Check if service started successfully
if ps -p $GOOGLE_ADS_PID > /dev/null; then
    echo "Google Ads ETL service started successfully (PID: $GOOGLE_ADS_PID)"
else
    echo "Warning: Google Ads ETL service failed to start"
fi

# Check PostgreSQL connection
echo "Checking database connection..."
if python -c "import sqlalchemy; import os; engine = sqlalchemy.create_engine(f'postgresql://{os.environ.get(\"PGUSER\")}:{os.environ.get(\"PGPASSWORD\")}@{os.environ.get(\"PGHOST\")}:{os.environ.get(\"PGPORT\")}/{os.environ.get(\"POSTGRES_DB\", \"railway\")}'); conn = engine.connect(); conn.close(); print('Database connection successful!')"; then
    echo "Database connection confirmed!"
else
    echo "Warning: Could not connect to database"
fi

# Run database initialization script
echo "Initializing database..."
python /app/src/api/db_init.py

# Start the API server
echo "Starting web server..."
cd /app
exec uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
